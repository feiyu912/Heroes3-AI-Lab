"""events-v3: one real isolated episode with CORRECT event attribution.

Fixes vs run_episode_events.py (v2), per WORKBUDDY_EVENTS_V2_REVIEW_20261018.md:
  P1-a: v2 attached obs['battle_events'] (events since OUR LAST turn) to the
        decision as if they belonged to the chosen action. v3 records them
        explicitly as `pre_events` and captures the events RETURNED by
        env.step(action) as `post_events` (the interaction that our action
        caused, including later opponent actions).
  P1-b: v2 never archived the events of the final step (loop exits right
        after step). v3 records terminal events of the last observation.
  Each event batch carries a monotonic `seq`; each decision records
  round_before/round_after and the ATTACK groups attributed to the executed
  action via the ACTION_STARTED/FINISHED of our side (single-env: our side
  acts exactly once per step, so the first ACTION_STARTED with our side in
  the post batch is our action; attack groups with attacker_side == our side
  after it and before the next ACTION_STARTED of our side belong to it).
  P2:  a stable identity table is built from the initial lineup and from
        every event's unitId<->node cross-reference; missing units are
        'unknown', never silently chaff.
"""
import argparse
import fcntl
import gzip
import importlib.util
import json
import os
from pathlib import Path
import time
import traceback
from types import SimpleNamespace
import numpy as np
from lab_io import atomic_json
from events_provenance import freeze, verify, digest
from battle_outcome_audit import audit
from experts_events import choose, counter_choose, bait_choose, bait_counter_choose, assess, VERSION


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def pack(obs):
    return dict(
        nodes={name: array.tolist() for name, array in obs['nodes'].items()},
        edges=[dict(relation=list(key), index=edge['index'].tolist(), attrs=edge['attrs'].tolist())
               for key, edge in obs['edges'].items()],
        active_action_ids=[int(action) for action in obs['active_action_ids']])


def unpack(data, side):
    return dict(
        nodes={name: np.asarray(array, np.float32) for name, array in data['nodes'].items()},
        edges={tuple(edge['relation']): dict(index=np.asarray(edge['index'], np.int64),
               attrs=np.asarray(edge['attrs'], np.float32)) for edge in data['edges']},
        active_action_ids=np.asarray(data['active_action_ids'], np.int64), lab_side=side)


def round_of(obs):
    from vcmi_gym.envs.v15.vcmi_env import Global
    return int(Global.decode_one(obs['nodes']['Global'][0]).BATTLE_ROUND)


def unit_flags(obs):
    from vcmi_gym.envs.v15.vcmi_env import Unit
    return {i: dict(is_enemy=bool(u.IS_ENEMY), value=float(u.VALUE_REL),
                    breath=bool(u.HAS_TWO_HEX_ATTACK_BREATH), cloud=bool(u.HAS_DEATH_CLOUD),
                    non_living=bool(u.HAS_NON_LIVING))
            for i, u in enumerate(Unit.decode_many(obs['nodes']['Unit']))}


def attribute_action_events(events, our_side):
    """Split a post-events batch around OUR executed action.

    Single-env: our side is asked exactly once per step, so the FIRST
    ACTION_STARTED with side == our_side starts our action. Its matching
    ACTION_FINISHED (same side + stack) closes it.
      action_attacks   : our attack groups strictly INSIDE our action window
      followup_ours     : our attack groups AFTER our action (automatic
                         retaliations we did not choose)
      window_enemy      : enemy attack groups inside our window (e.g. the
                         target's automatic counter to our attack)
    Returns (action_attacks, our_start_index, followup_ours, window_enemy).
    """
    starts = [i for i, e in enumerate(events)
              if e['kind'] == 0 and e.get('side', -1) == our_side]
    if not starts:
        return [], None, [], []
    begin = starts[0]
    stack = events[begin].get('stack_number')
    end = None
    for i in range(begin + 1, len(events)):
        e = events[i]
        if e['kind'] == 1 and e.get('side', -1) == our_side and e.get('stack_number') == stack:
            end = i
            break
    if end is None:
        end = len(events)
    action_attacks = [e for e in events[begin + 1:end]
                      if e['kind'] == 2 and e.get('attacker_side', -1) == our_side]
    followup_ours = [e for e in events[end:]
                     if e['kind'] == 2 and e.get('attacker_side', -1) == our_side]
    window_enemy = [e for e in events[begin + 1:end]
                    if e['kind'] == 2 and e.get('attacker_side', -1) != our_side]
    return action_attacks, begin, followup_ours, window_enemy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', type=int, required=True)
    parser.add_argument('--role', choices=['attacker', 'defender'], required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--policy', choices=['expert', 'counter', 'bait', 'bait-counter',
                                             'teacher', 'model', 'random'], required=True)
    parser.add_argument('--checkpoint', default='')
    parser.add_argument('--scenario-file', default='scenarios-v3.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    research = here.parents[1] / 'research'
    cases = json.loads((here / args.scenario_file).read_text())
    case = cases[args.scenario]
    output = Path(args.output)
    assert not output.exists(), 'Preserve previous episode evidence'
    output.parent.mkdir(parents=True, exist_ok=True)
    pool = Path('/root/heroes3-ai-lab/evaluations/.pool-lock')
    with pool.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                             if line.startswith('MemAvailable:')))
        assert available > 4096 * 1024, 'Leave memory for the active training/evaluation pipeline'
        protocol = SimpleNamespace(
            scenario_file=str(here / args.scenario_file), scenarios=[args.scenario],
            policies=['recovered'] if args.policy == 'model' else ['scripted'],
            checkpoint=args.checkpoint, opponent='BattleAI')
        frozen = freeze(protocol)
        for path in sorted(here.glob('*.py')):
            frozen[str(path)] = digest(path)
        os.environ['LAB_BATTLEAI_TEACHER'] = '1' if args.policy in (
            'expert', 'counter', 'bait', 'bait-counter', 'teacher') else '0'
        os.environ['LAB_BATTLEAI_TEACHER_TURNS'] = '2'
        from vcmi_gym.envs.v15.vcmi_env import VcmiEnv
        model = None
        if args.policy == 'model':
            import torch
            torch.set_num_threads(1)
            model = module('tactic_model', research / 'recovered-graph.py').RecoveredPair(args.checkpoint).eval().models[args.role]
        rng = np.random.default_rng(args.seed)
        env = VcmiEnv(
            mapname=case['map'], seed=args.seed, role=args.role, opponent='BattleAI',
            random_heroes=0, random_obstacles=0, town_chance=0, warmachine_chance=0,
            random_armies=False, mana_min=0, mana_max=0,
            tight_formation_chance=case['tight_formation_chance'],
            user_timeout=120, vcmi_timeout=120, boot_timeout=120,
            vcmi_loglevel_global='error', vcmi_loglevel_ai='error')
        started = time.monotonic()
        our_side = int(args.role == 'defender')
        seq = 0
        step_log = []
        identity = {}   # unit_id -> identity record (first time seen in any event)
        event_counts = dict(reset=0, pre=0, post=0, terminal=0)
        excluded_invalid = 0
        try:
            obs, _ = env.reset()
            reset_events = obs.get('battle_events', [])
            event_counts['reset'] = len(reset_events)
            initial_flags = unit_flags(obs)
            initial_lineup = {f'node{i}': f for i, f in initial_flags.items()}
            terminated = truncated = False
            while not (terminated or truncated):
                pre_events = obs.get('battle_events', [])
                event_counts['pre'] += len(pre_events)
                cur_flags = unit_flags(obs)
                # cross-reference events' unit ids <-> node indices of THIS decision
                for e in pre_events:
                    for uid, node in [(e.get('attacker_id'), e.get('attacker_node')),
                                      (e.get('stack_number'), e.get('stack_node'))]:
                        if uid is None or uid < 0 or node is None or node < 0:
                            continue
                        rec = identity.setdefault(int(uid), {})
                        rec.setdefault('node_first_seen', int(node))
                        rec.setdefault('side', e.get('side', e.get('attacker_side')))
                        rec.setdefault('identity', cur_flags.get(int(node), dict(unknown=True)))
                        rec['seen_in_decisions'] = rec.get('seen_in_decisions', 0) + 1
                    for t in e.get('targets', []):
                        for uid, node in [(t.get('defender_id'), t.get('defender_node')),
                                          (t.get('attacker_id'), t.get('attacker_node'))]:
                            if uid is None or uid < 0 or node is None or node < 0:
                                continue
                            rec = identity.setdefault(int(uid), {})
                            rec.setdefault('node_first_seen', int(node))
                            rec.setdefault('side', t.get('defender_side', t.get('attacker_side')))
                            rec.setdefault('identity', cur_flags.get(int(node), dict(unknown=True)))
                            rec['seen_in_decisions'] = rec.get('seen_in_decisions', 0) + 1
                legal = [int(action) for action in obs['active_action_ids']]
                round_before = round_of(obs)
                tick = time.perf_counter()
                if args.policy == 'expert':
                    action, quality = choose(obs)
                elif args.policy == 'counter':
                    action, quality = counter_choose(obs)
                elif args.policy == 'bait':
                    action, quality = bait_choose(obs)
                elif args.policy == 'bait-counter':
                    action, quality = bait_counter_choose(obs)
                elif args.policy == 'teacher':
                    action = int(obs['teacher_action_id'])
                    quality = dict(version='native-BattleEvaluator-depth2', quality='unfiltered-search-candidate')
                elif args.policy == 'random':
                    action = int(rng.choice(legal))
                    quality = dict(version='legal-random-v1', quality='random-control')
                else:
                    with torch.inference_mode():
                        logits, value = model(obs)
                    assert torch.isfinite(logits).all() and torch.isfinite(value).all()
                    action = legal[int(logits.argmax())]
                    quality = dict(version=digest(args.checkpoint), quality='model-baseline')
                latency = (time.perf_counter() - tick) * 1000
                if action not in legal:
                    excluded_invalid += 1
                    assert False, 'Illegal action selected'
                facts = assess(obs)
                obs_next, _, terminated, truncated, _ = env.step(action)
                post_events = obs_next.get('battle_events', [])
                post_flags = unit_flags(obs_next)
                event_counts['post'] += len(post_events)
                action_attacks, our_start, followup_ours, window_enemy = \
                    attribute_action_events(post_events, our_side)
                step_log.append(dict(
                    seq=seq, round_before=round_before,
                    round_after=round_of(obs_next),
                    pre_flags=cur_flags, post_flags=post_flags,
                    legal_actions=legal,
                    expert_action=action if args.policy in ('expert', 'counter', 'bait', 'bait-counter') else None,
                    executed_action=action,
                    actor_side=our_side, tactic_id=case['tactic_id'],
                    battle_id=output.stem, scenario_seed=args.seed, policy=args.policy,
                    expert_version=quality['version'], quality=quality,
                    selected_facts=facts[action],
                    pre_events=pre_events, post_events=post_events,
                    action_attack_groups=action_attacks,
                    followup_own_attack_groups=followup_ours,
                    window_enemy_attack_groups=window_enemy,
                    our_action_event_index=our_start,
                    decision_latency_ms=latency,
                    terminated=bool(terminated), truncated=bool(truncated)))
                seq += 1
                obs = obs_next
                if len(step_log) >= 400 and not terminated:
                    truncated = True
            # terminal batch: events of the final observation were NOT archived by v2
            terminal_events = obs.get('battle_events', [])
            event_counts['terminal'] = len(terminal_events)
            cur_flags = unit_flags(obs)
            # cross-reference terminal events into the identity table too
            for e in terminal_events:
                for uid, node in [(e.get('attacker_id'), e.get('attacker_node')),
                                  (e.get('stack_number'), e.get('stack_node'))]:
                    if uid is None or uid < 0 or node is None or node < 0:
                        continue
                    rec = identity.setdefault(int(uid), {})
                    rec.setdefault('node_first_seen', int(node))
                    rec.setdefault('side', e.get('side', e.get('attacker_side')))
                    rec.setdefault('identity', cur_flags.get(int(node), dict(unknown=True)))
                for t in e.get('targets', []):
                    for uid, node in [(t.get('defender_id'), t.get('defender_node')),
                                      (t.get('attacker_id'), t.get('attacker_node'))]:
                        if uid is None or uid < 0 or node is None or node < 0:
                            continue
                        rec = identity.setdefault(int(uid), {})
                        rec.setdefault('node_first_seen', int(node))
                        rec.setdefault('side', t.get('defender_side', t.get('attacker_side')))
                        rec.setdefault('identity', cur_flags.get(int(node), dict(unknown=True)))
            outcome = json.loads(json.dumps(obs.get('terminal_outcome')))
            side = our_side
            success = bool(terminated and not truncated and outcome and outcome['result_type'] == 0 and outcome['winner'] == side)
            losses = outcome['casualties'][str(side)] if outcome else None
            n_attacks = sum(1 for s in step_log for e in s['post_events'] if e['kind'] == 2)
            n_counter = sum(1 for s in step_log for e in s['post_events']
                            if e['kind'] == 2 and (e['attack_flags'] & 2))
            n_secondary = sum(1 for s in step_log for e in s['post_events']
                              if e['kind'] == 2 for t in e['targets'] if (t['flags'] & 2))
            record = dict(
                schema='human-tactics-demonstration-events-v3', completed=True,
                battle_id=output.stem, scenario=case['id'], split=case['split'],
                tactic_id=case['tactic_id'], role=args.role, seed=args.seed, policy=args.policy,
                checkpoint=args.checkpoint, terminated=bool(terminated), truncated=bool(truncated),
                terminal_outcome=outcome, success=success, invalid_actions=excluded_invalid,
                permanent_army_loss_by_creature=losses,
                permanent_army_loss_units=sum(losses.values()) if losses else 0,
                steps=len(step_log),
                event_counts=event_counts,
                native_attacks=n_attacks, native_counter_attacks=n_counter,
                native_secondary_hits=n_secondary,
                initial_lineup=initial_lineup, event_identity=identity,
                mean_decision_latency_ms=float(np.mean([s['decision_latency_ms'] for s in step_log])) if step_log else 0.0,
                wall_seconds=time.monotonic() - started, frozen_artifacts=frozen,
                limitations='pre_events are interactions since our previous turn; post_events are the '
                            'interaction caused by (and following) the executed action; attributed_action_events '
                            'are only our own action attack groups. terminal_events are archived separately. '
                            'A post batch may span a round boundary (round_before/round_after recorded).')
            record['raw_outcome_audit'] = audit([record])
            verify(frozen)
            archive = output.with_suffix('.json.gz')
            temporary = archive.with_name(archive.name + '.tmp')
            with gzip.open(temporary, 'wt') as stream:
                json.dump(dict(episode=record, reset_events=reset_events,
                               step_log=step_log, terminal_events=terminal_events), stream)
            os.replace(temporary, archive)
            record.update(demonstrations=str(archive), demonstration_sha256=digest(archive))
            atomic_json(output, record)
            print(json.dumps({key: record[key] for key in
                  ['scenario', 'policy', 'success', 'steps', 'native_attacks',
                   'native_counter_attacks', 'native_secondary_hits', 'event_counts']}), flush=True)
        except BaseException:
            atomic_json(output, dict(completed=False, error=traceback.format_exc(), config=vars(args)))
            raise
        finally:
            env.close()


if __name__ == '__main__':
    main()
