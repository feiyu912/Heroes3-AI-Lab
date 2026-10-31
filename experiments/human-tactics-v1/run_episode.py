"""One real isolated episode, full structured demonstrations, strict outcomes."""
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
from evaluation_provenance import freeze, verify, digest
from battle_outcome_audit import audit
from experts import choose, assess, VERSION


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def pack(obs):
    return dict(nodes={name: array.tolist() for name, array in obs['nodes'].items()},
        edges=[dict(relation=list(key), index=edge['index'].tolist(), attrs=edge['attrs'].tolist())
               for key, edge in obs['edges'].items()],
        active_action_ids=[int(action) for action in obs['active_action_ids']])


def unpack(data, side):
    return dict(nodes={name: np.asarray(array, np.float32) for name, array in data['nodes'].items()},
        edges={tuple(edge['relation']): dict(index=np.asarray(edge['index'], np.int64),
               attrs=np.asarray(edge['attrs'], np.float32)) for edge in data['edges']},
        active_action_ids=np.asarray(data['active_action_ids'], np.int64), lab_side=side)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', type=int, required=True)
    parser.add_argument('--role', choices=['attacker', 'defender'], required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--policy', choices=['expert', 'teacher', 'model'], required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    research = here.parents[1]/'research'
    cases = json.loads((here/'scenarios.json').read_text())
    case = cases[args.scenario]
    output = Path(args.output)
    assert not output.exists(), 'Preserve previous episode evidence'
    output.parent.mkdir(parents=True, exist_ok=True)
    pool = Path('/root/heroes3-ai-lab/evaluations/.pool-lock')
    with pool.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
        assert available > 4096*1024, 'Leave memory for the active training/evaluation pipeline'
        protocol = SimpleNamespace(scenario_file=str(here/'scenarios.json'), scenarios=[args.scenario],
            policies=['recovered'], checkpoint=args.checkpoint, opponent='BattleAI')
        frozen = freeze(protocol)
        for path in here.glob('*.py'):
            frozen[str(path)] = digest(path)
        os.environ['LAB_BATTLEAI_TEACHER'] = '1' if args.policy != 'model' else '0'
        os.environ['LAB_BATTLEAI_TEACHER_TURNS'] = '2'
        from vcmi_gym.envs.v15.vcmi_env import VcmiEnv
        model = None
        if args.policy == 'model':
            import torch
            torch.set_num_threads(1)
            model = module('tactic_model', research/'recovered-graph.py').RecoveredPair(args.checkpoint).eval().models[args.role]
        env = VcmiEnv(mapname=case['map'], seed=args.seed, role=args.role, opponent='BattleAI',
            random_heroes=0, random_obstacles=0, town_chance=0, warmachine_chance=0,
            random_armies=False, mana_min=0, mana_max=0,
            tight_formation_chance=case['tight_formation_chance'],
            user_timeout=120, vcmi_timeout=120, boot_timeout=120,
            vcmi_loglevel_global='error', vcmi_loglevel_ai='error')
        started = time.monotonic()
        decisions = []
        try:
            obs, _ = env.reset()
            terminated = truncated = False
            while not (terminated or truncated):
                legal = [int(action) for action in obs['active_action_ids']]
                tick = time.perf_counter()
                if args.policy == 'expert':
                    action, quality = choose(obs)
                elif args.policy == 'teacher':
                    action = int(obs['teacher_action_id'])
                    quality = dict(version='native-BattleEvaluator-depth2', quality='unfiltered-search-candidate')
                else:
                    with torch.inference_mode():
                        logits, value = model(obs)
                    assert torch.isfinite(logits).all() and torch.isfinite(value).all()
                    action = legal[int(logits.argmax())]
                    quality = dict(version=digest(args.checkpoint), quality='model-baseline')
                latency = (time.perf_counter()-tick)*1000
                assert action in legal, 'Illegal expert/model action'
                facts = assess(obs)
                decisions.append(dict(observation=pack(obs), legal_actions=legal,
                    expert_action=action if args.policy != 'model' else None, executed_action=action,
                    actor_side=int(args.role=='defender'), tactic_id=case['tactic_id'],
                    battle_id=output.stem, scenario_seed=args.seed, policy=args.policy,
                    expert_version=quality['version'], quality=quality,
                    selected_facts=facts[action],
                    multi_target_available=any(f['ability'] and f['enemy_targets']>=2 for f in facts.values()),
                    decision_latency_ms=latency))
                obs, _, terminated, truncated, _ = env.step(action)
                if len(decisions) >= 400 and not terminated:
                    truncated = True
            # Native outcome dictionaries use integer keys; JSON artifacts use
            # strings. Normalize once before losses and the shared raw audit.
            outcome = json.loads(json.dumps(obs.get('terminal_outcome')))
            side = int(args.role == 'defender')
            success = bool(terminated and not truncated and outcome and outcome['result_type']==0 and outcome['winner']==side)
            losses = outcome['casualties'][str(side)] if outcome else None
            record = dict(schema='human-tactics-demonstration-v1', completed=True,
                battle_id=output.stem, scenario=case['id'], split=case['split'],
                tactic_id=case['tactic_id'], role=args.role, seed=args.seed, policy=args.policy,
                checkpoint=args.checkpoint, terminated=bool(terminated), truncated=bool(truncated),
                terminal_outcome=outcome, success=success, invalid_actions=0,
                permanent_army_loss_by_creature=losses, permanent_army_loss_units=sum(losses.values()) if losses else 0,
                steps=len(decisions), multi_target_opportunities=sum(row['multi_target_available'] for row in decisions),
                selected_multi_enemy_attacks=sum(row['selected_facts']['ability'] and row['selected_facts']['enemy_targets']>=2 for row in decisions),
                selected_friendly_targets=sum(row['selected_facts']['friendly_targets'] for row in decisions),
                mean_decision_latency_ms=float(np.mean([row['decision_latency_ms'] for row in decisions])),
                wall_seconds=time.monotonic()-started, frozen_artifacts=frozen,
                quality_tier='normal-win-candidate' if success else 'failure-or-loss-retained',
                limitations='Coverage is not actual damage, tactical success or proof of optimality. Retaliation usage/counter has not been causally instrumented. No resurrection/summoning fixtures.')
            record['raw_outcome_audit'] = audit([record])
            verify(frozen)
            archive = output.with_suffix('.json.gz')
            temporary = archive.with_name(archive.name+'.tmp')
            with gzip.open(temporary, 'wt') as stream:
                json.dump(dict(episode=record, decisions=decisions), stream)
            os.replace(temporary, archive)
            record.update(demonstrations=str(archive), demonstration_sha256=digest(archive))
            atomic_json(output, record)
            print(json.dumps({key: record[key] for key in ['scenario','policy','success','steps','multi_target_opportunities','selected_multi_enemy_attacks']}), flush=True)
        except BaseException:
            atomic_json(output, dict(completed=False, error=traceback.format_exc(), config=vars(args)))
            raise
        finally:
            env.close()


if __name__ == '__main__':
    main()
