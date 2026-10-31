"""Record real learner-turn observations for tactical review, not skill scores."""
import argparse
import fcntl
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import torch
from lab_io import atomic_json
from evaluation_provenance import freeze, verify, digest
from observation_digest import update as update_digest
from vcmi_gym.envs.v15.vcmi_env import Action, Global, Unit, ACTION_TYPES


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--scenarios', required=True)
    parser.add_argument('--scenario', type=int, required=True)
    parser.add_argument('--role', choices=['attacker', 'defender'], required=True)
    parser.add_argument('--seed', type=int, default=2026102701)
    parser.add_argument('--opponent', choices=['BattleAI', 'VIPBot'], default='BattleAI')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    research = Path(__file__).resolve().parent
    case = json.loads(Path(args.scenarios).read_text())[args.scenario]
    assert case['split'] == 'train', 'Diagnostic trace is restricted to training maps'
    output = Path(args.output)
    assert not output.exists(), 'Preserve existing traces'
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path('/root/heroes3-ai-lab/evaluations/.pool-lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        available = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                             if line.startswith('MemAvailable:')))
        assert available > 4096 * 1024, 'Insufficient memory reserve for overlapping one CPU diagnostic'
        protocol = SimpleNamespace(scenario_file=args.scenarios, scenarios=[args.scenario],
            policies=['recovered'], checkpoint=args.checkpoint, opponent=args.opponent)
        frozen = freeze(protocol)
        frozen[str(Path(__file__).resolve())] = digest(__file__)
        os.environ['LAB_BATTLEAI_TEACHER'] = '0'
        torch.set_num_threads(1)
        model = load_module('trace_recovered', research / 'recovered-graph.py').RecoveredPair(
            args.checkpoint).eval().models[args.role]
        lab = load_module('trace_lab', research / 'lab-env.py')
        env = lab.make_env(case['map'], args.seed, args.role, opponent=args.opponent)
        temporary = output.with_name(output.name + '.tmp')
        count = 0
        trajectory = hashlib.sha256()
        types = {value: name for name, value in ACTION_TYPES.items()}
        try:
            obs, _ = env.reset()
            term = trunc = False
            with gzip.open(temporary, 'wt', encoding='utf-8') as stream:
                while not (term or trunc):
                    ids = [int(value) for value in obs['active_action_ids']]
                    with torch.inference_mode():
                        logits, value = model(obs)
                    assert torch.isfinite(logits).all() and torch.isfinite(value).all()
                    action = ids[int(logits.argmax())]
                    decoded = Action.decode_one(obs['nodes']['Action'][action])
                    selected_edges = []
                    for key, edge in obs['edges'].items():
                        if 'Action' not in (key[0], key[2]):
                            continue
                        axis = 0 if key[0] == 'Action' else 1
                        for index in range(edge['index'].shape[1]):
                            if int(edge['index'][axis, index]) == action:
                                selected_edges.append(dict(relation=list(key),
                                    endpoints=edge['index'][:, index].tolist(),
                                    attributes=edge['attrs'][index].tolist()))
                    update_digest(trajectory, obs)
                    record = dict(step=count, action_id=action, action_type=types[int(decoded.ACTION_TYPE)],
                        global_state=Global.decode_one(obs['nodes']['Global'][0])._asdict(),
                        units=[unit._asdict() for unit in Unit.decode_many(obs['nodes']['Unit'])],
                        legal_action_ids=ids, selected_edges=selected_edges,
                        nodes={key: array.tolist() for key, array in obs['nodes'].items()},
                        edges=[dict(relation=list(key), index=edge['index'].tolist(),
                                    attrs=edge['attrs'].tolist()) for key, edge in obs['edges'].items()])
                    stream.write(json.dumps(record) + '\n')
                    obs, _, term, trunc, _ = env.step(action)
                    count += 1
                    if count >= 400 and not term:
                        trunc = True
                stream.write(json.dumps(dict(final=True, terminated=bool(term), truncated=bool(trunc),
                    terminal_outcome=obs.get('terminal_outcome'))) + '\n')
            verify(frozen)
            os.replace(temporary, output)
            # Native shutdown may end the process; finish durable artifacts first.
            with gzip.open(output, 'rt', encoding='utf-8') as stream:
                records = [json.loads(line) for line in stream]
            assert len(records) == count + 1 and records[-1]['final']
            assert all(row['action_id'] in row['legal_action_ids'] for row in records[:-1])
            report = dict(completed=True, scenario=case['id'], role=args.role, opponent=args.opponent,
                steps=count, terminated=bool(term), truncated=bool(trunc),
                terminal_outcome=obs.get('terminal_outcome'), frozen_artifacts=frozen,
                trace=str(output), trace_sha256=digest(output), trajectory_sha256=trajectory.hexdigest(),
                scope='Training-map diagnostic only; observations occur at learner turns, so transitions include intervening opponent actions. Unit row indices are local to each observation, not persistent IDs. No causal tactic label or independent strength claim.')
            atomic_json(output.with_suffix('.manifest.json'), report)
            print(json.dumps({key: report[key] for key in ['completed', 'scenario', 'steps', 'terminated', 'truncated', 'trace_sha256']}), flush=True)
        finally:
            if temporary.exists():
                temporary.unlink()
            env.close()


if __name__ == '__main__':
    main()
