"""Versioned replacement: one step -> one returned event batch, terminal included."""
import argparse
import fcntl
import gzip
import json
import os
from pathlib import Path
import time
import traceback
import shutil
import re
import hashlib
import numpy as np
from events_provenance import digest, freeze, verify
from event_audit import update_identity, action_window, analyze_retaliations, demonstration_gate


def packed(obs):
    return dict(nodes={k: a.tolist() for k, a in obs['nodes'].items()},
                edges=[dict(relation=list(k), index=v['index'].tolist(), attrs=v['attrs'].tolist())
                       for k, v in obs['edges'].items()],
                active_action_ids=[int(a) for a in obs['active_action_ids']])


def flags(obs):
    from vcmi_gym.envs.v15.vcmi_env import Unit
    return {str(i): dict(is_enemy=bool(u.IS_ENEMY), value_relative=float(u.VALUE_REL),
                         breath=bool(u.HAS_TWO_HEX_ATTACK_BREATH), cloud=bool(u.HAS_DEATH_CLOUD),
                         non_living=bool(u.HAS_NON_LIVING))
            for i, u in enumerate(Unit.decode_many(obs['nodes']['Unit']))}


def round_number(obs):
    from vcmi_gym.envs.v15.vcmi_env import Global
    return int(Global.decode_one(obs['nodes']['Global'][0]).BATTLE_ROUND)


def atomic(path, value):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, indent=2))
    os.replace(temp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', type=int, required=True)
    ap.add_argument('--scenario-file', default='scenarios.json')
    ap.add_argument('--teacher-turns',type=int,choices=(2,4,10),default=2)
    ap.add_argument('--reference',required=True)
    ap.add_argument('--pivot-step',type=int,required=True)
    ap.add_argument('--intervention',choices=('none','WAIT'),required=True)
    ap.add_argument('--role', choices=('attacker', 'defender'), required=True)
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--policy', choices=('teacher', 'expert', 'counter', 'bait', 'bait-counter', 'random'), required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    scenario_file = here / args.scenario_file
    case = json.loads(scenario_file.read_text())[args.scenario]
    with gzip.open(args.reference,'rt') as f:
        reference=json.load(f)
    reference_ep=reference['episode']
    assert reference_ep['seed']==args.seed and reference_ep['role']==args.role and reference_ep['scenario']==case['id']
    assert reference_ep['teacher_horizon']==args.teacher_turns
    assert 0<=args.pivot_step<len(reference['transitions'])
    obs_hash=lambda graph:hashlib.sha256(json.dumps(graph,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    output = Path(args.output)
    assert not output.exists() and not output.with_suffix('.json.gz').exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    side = int(args.role == 'defender')
    started = time.monotonic()
    lock_path = Path('/root/heroes3-ai-lab/evaluations/.pool-lock')
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        frozen = freeze(case, scenario_file)
        frozen[str(Path(args.reference).resolve())]=digest(args.reference)
        snapshot = output.parent / 'source-snapshots'
        snapshot.mkdir(exist_ok=True)
        for path, checksum in frozen.items():
            if Path(path).suffix in ('.py', '.sh', '.json'):
                dest = snapshot / (checksum + '-' + Path(path).name)
                if not dest.exists():
                    shutil.copyfile(path, dest)
        os.environ['LAB_BATTLEAI_TEACHER'] = '1' if args.policy != 'random' else '0'
        os.environ['LAB_BATTLEAI_TEACHER_TURNS'] = str(args.teacher_turns)
        from vcmi_gym.envs.v15.vcmi_env import VcmiEnv, Action, ACTION_TYPES
        from experts_events import choose, counter_choose, bait_choose, bait_counter_choose, assess
        policies = dict(expert=choose, counter=counter_choose, bait=bait_choose, **{'bait-counter': bait_counter_choose})
        env = VcmiEnv(mapname=case['map'], seed=args.seed, role=args.role, opponent='BattleAI',
                      random_heroes=0, random_obstacles=0, town_chance=0, warmachine_chance=0,
                      random_armies=False, mana_min=0, mana_max=0,
                      tight_formation_chance=case['tight_formation_chance'],
                      user_timeout=120, vcmi_timeout=120, boot_timeout=120,
                      vcmi_loglevel_global='error', vcmi_loglevel_ai='error')
        batches, transitions, identity = [], [], {}
        rng = np.random.default_rng(args.seed)
        try:
            obs, _ = env.reset()
            initial_observation = packed(obs)
            def add_batch(observation, before_round, caused_by):
                verify(frozen)
                events = observation['battle_events']
                assert isinstance(events, list)
                batch = dict(batch_id=len(batches), caused_by_step=caused_by,
                             round_before=before_round, round_after=round_number(observation),
                             events=events, observation_flags=flags(observation))
                mapping = update_identity(identity, events, batch['observation_flags'], batch['batch_id'])
                batches.append(batch)
                return batch, mapping
            batch, mapping = add_batch(obs, None, None)
            terminated = truncated = False
            while not (terminated or truncated):
                step = len(transitions)
                legal = [int(a) for a in obs['active_action_ids']]
                # Audit events and outcomes are explicitly withheld from every policy.
                policy_obs = {k: v for k, v in obs.items() if k not in ('battle_events', 'terminal_outcome')}
                if args.policy == 'teacher':
                    action, quality = int(obs['teacher_action_id']), dict(version=f'native-horizon-{args.teacher_turns}', certified=False)
                elif args.policy == 'random':
                    action, quality = int(rng.choice(legal)), dict(version='random', certified=False)
                else:
                    action, quality = policies[args.policy](policy_obs)
                expected_prefix_hash=None
                actual_prefix_hash=None
                if step<=args.pivot_step:
                    old_step=reference['transitions'][step]
                    expected_prefix_hash=obs_hash(old_step['observation_before'])
                    actual_prefix_hash=obs_hash(packed(obs))
                    assert expected_prefix_hash==actual_prefix_hash, f'Prefix graph mismatch at step {step}'
                    assert legal==old_step['legal_actions'], f'Prefix legal actions mismatch at step {step}'
                    action=old_step['executed_action']
                    quality=dict(version='reference-prefix-replay-v1',certified=False,reference_action=action)
                    if step==args.pivot_step and args.intervention=='WAIT':
                        alternatives=[a for a in legal if int(Action.decode_one(obs['nodes']['Action'][a]).ACTION_TYPE)==ACTION_TYPES['WAIT']]
                        assert len(alternatives)==1 and alternatives[0]!=action,'No distinct legal WAIT at pivot'
                        quality.update(version='controlled-WAIT-intervention-v1',reference_action=action)
                        action=alternatives[0]
                assert action in legal
                selected = assess(policy_obs)[action]
                known_actor = mapping.get(selected['actor_node'])
                pre = packed(obs)
                before = round_number(obs)
                action_kind = int(Action.decode_one(obs['nodes']['Action'][action]).ACTION_TYPE)
                teacher_description=obs.get('teacher_action_description','')
                timing=re.search(r'teacher_eval_us=(\d+)',teacher_description)
                assert timing is not None, 'Native teacher timing missing; refuse to invent CPU search cost'
                obs_next, reward, terminated, truncated, info = env.step(action)
                post, next_mapping = add_batch(obs_next, before, step)
                native_type = {ACTION_TYPES['WAIT']: 6, ACTION_TYPES['DEFEND']: 7,
                               ACTION_TYPES['MOVE']: 5, ACTION_TYPES['AMOVE']: 8,
                               ACTION_TYPES['SHOOT']: 9}[action_kind]
                window = action_window(post['events'], side, known_actor, native_type)
                # If actor survived, independently cross-check returned node metadata.
                actor_id = window.get('actor_id')
                if actor_id is not None and str(actor_id) in identity:
                    known_side = identity[str(actor_id)]['side']
                    assert known_side in (None, side)
                row = dict(step_id=step, actor_side=side, legal_actions=legal,
                           executed_action=action, graph_action_type=action_kind,
                           known_actor_id_before=known_actor, selected_facts=selected, quality=quality,
                           teacher_horizon=args.teacher_turns,teacher_description=teacher_description,
                           teacher_eval_us=int(timing.group(1)),
                           expected_prefix_obs_sha256=expected_prefix_hash,actual_prefix_obs_sha256=actual_prefix_hash,
                           observation_before=pre, observation_after=packed(obs_next),
                           pre_batch_id=batch['batch_id'], post_batch_id=post['batch_id'],
                           action_window=window, reward=float(reward),
                           terminated=bool(terminated), truncated=bool(truncated))
                transitions.append(row)
                obs, batch, mapping = obs_next, post, next_mapping
                if step >= 399 and not terminated:
                    truncated = True
            outcome = obs.get('terminal_outcome')
            summary = dict(schema='human-events-v3.1', completed=True, battle_id=output.stem,
                           scenario=case['id'], original_split=case['split'], data_use='engineering-audit-only',
                           policy=args.policy, role=args.role, seed=args.seed, tactic_id=case['tactic_id'],
                           teacher_horizon=args.teacher_turns,
                           reference_archive=str(Path(args.reference).resolve()),reference_archive_sha256=digest(args.reference),
                           intervention_step=args.pivot_step,intervention=args.intervention,
                           matched_prefix_decisions=sum(t['expected_prefix_obs_sha256'] is not None for t in transitions),
                           terminated=bool(terminated), truncated=bool(truncated), invalid_actions=0,
                           terminal_outcome=outcome, steps=len(transitions), event_batches=len(batches),
                           terminal_batch_id=batch['batch_id'],
                           terminal_event_count=sum(e['kind'] == 3 for e in batch['events']),
                           matched_action_windows=sum(t['action_window']['status'] == 'matched' for t in transitions),
                           unknown_identities=sum(v['unknown'] for v in identity.values()),
                           frozen_artifacts=frozen, wall_seconds=time.monotonic()-started)
            summary['success'] = bool(terminated and not truncated and outcome and outcome['result_type'] == 0 and outcome['winner'] == side)
            for t in transitions:
                t['demonstration_gate'] = demonstration_gate(t, batches[t['post_batch_id']]['events'], summary)
            summary['event_verified_decisions'] = sum(t['demonstration_gate']['action_event_verified'] for t in transitions)
            teacher_times=[t['teacher_eval_us'] for t in transitions]
            summary.update(teacher_cpu_eval_total_us=sum(teacher_times),
                           teacher_cpu_eval_mean_us=float(np.mean(teacher_times)),
                           teacher_cpu_eval_p95_us=float(np.percentile(teacher_times,95)))
            summary['bc_eligible_decisions'] = 0
            raw = dict(episode=summary, initial_observation=initial_observation,
                       batches=batches, transitions=transitions, stable_identity=identity,
                       retaliation_audit=analyze_retaliations(batches))
            verify(frozen)
            archive = output.with_suffix('.json.gz')
            temp = archive.with_name(archive.name + '.tmp')
            with gzip.open(temp, 'wt') as f:
                json.dump(raw, f)
            os.replace(temp, archive)
            summary.update(archive=str(archive), archive_sha256=digest(archive))
            atomic(output, summary)
            print(json.dumps({k:summary[k] for k in ('battle_id','steps','matched_action_windows','terminal_event_count','success','event_verified_decisions')}), flush=True)
        except BaseException:
            atomic(output, dict(completed=False, error=traceback.format_exc(), args=vars(args),
                                steps_recorded=len(transitions), frozen_artifacts=frozen))
            # Preserve partial evidence too; it remains explicitly incomplete.
            with gzip.open(output.with_suffix('.partial.json.gz'), 'wt') as f:
                json.dump(dict(batches=batches, transitions=transitions, stable_identity=identity), f)
            raise
        finally:
            env.close()


if __name__ == '__main__':
    main()
