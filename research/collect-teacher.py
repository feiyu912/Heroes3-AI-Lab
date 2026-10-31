import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time
import numpy as np
from vcmi_gym.envs.v15.vcmi_env import Action, ACTION_TYPES, Global

spec = importlib.util.spec_from_file_location('lab_env', Path(__file__).with_name('lab-env.py'))
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)

parser = argparse.ArgumentParser()
parser.add_argument('--scenario', type=int, required=True)
parser.add_argument('--role', choices=['attacker', 'defender'], required=True)
parser.add_argument('--episodes', type=int, default=10)
parser.add_argument('--dataset', required=True)
parser.add_argument('--scenarios', default='/mnt/g/Heroes3-AI-Lab/research/scenarios-v1.json')
parser.add_argument('--seed-base', type=int, default=202610140)
args = parser.parse_args()
assert os.environ.get('LAB_BATTLEAI_TEACHER') == '1'
scenario = json.loads(Path(args.scenarios).read_text())[args.scenario]
seed = args.seed_base + args.scenario * 2 + int(args.role == 'defender')
folder = Path(args.dataset) / scenario['split']
folder.mkdir(parents=True, exist_ok=True)
env = lab.make_env(scenario['map'], seed, args.role)
started = time.monotonic()
all_records = []
for episode in range(args.episodes):
    battle_id = f"{scenario['id']}-{args.role}-s{seed}-b{episode}"
    arrays, decisions = {}, []
    obs, _ = env.reset()
    term = trunc = False
    while not (term or trunc):
        t = len(decisions)
        ids = np.asarray(obs['active_action_ids'], dtype=np.int64)
        teacher = int(obs.get('teacher_action_id', -1))
        desc = obs.get('teacher_action_description', '')
        if teacher not in ids:
            failure = dict(battle_id=battle_id, step=t, teacher_id=teacher,
                           description=desc, legal_ids=ids.tolist())
            (folder / (battle_id + '.failure.json')).write_text(json.dumps(failure, indent=2))
            raise RuntimeError(f'Teacher action could not be mapped: {failure}')
        digest = hashlib.sha256()
        for name, values in sorted(obs['nodes'].items()):
            values = np.asarray(values)
            assert np.isfinite(values).all()
            arrays[f'{t}/nodes/{name}'] = values
            digest.update(name.encode())
            digest.update(values.tobytes())
        for key, edge in obs['edges'].items():
            edge_name = '|'.join(key)
            for field, values in edge.items():
                arrays[f'{t}/edges/{edge_name}/{field}'] = values
                assert np.isfinite(values).all()
                digest.update(edge_name.encode() + field.encode())
                digest.update(values.tobytes())
        mask = np.zeros(len(obs['nodes']['Action']), dtype=np.bool_)
        mask[ids] = True
        assert len(ids) == len(set(ids.tolist())) and mask[teacher]
        arrays[f'{t}/legal_ids'] = ids
        arrays[f'{t}/mask'] = mask
        decoded = Action.decode_one(obs['nodes']['Action'][teacher])
        decisions.append(dict(action=teacher, action_type=int(decoded.ACTION_TYPE),
                              teacher_description=desc, observation_sha256=digest.hexdigest(),
                              candidate_count=len(ids)))
        obs, _, term, trunc, info = env.step(teacher)
    assert term and not trunc, f'{battle_id}: battle did not finish normally'
    outcome = obs['terminal_outcome']
    assert outcome and outcome['result_type'] == 0
    side = int(args.role == 'defender')
    record = dict(battle_id=battle_id, scenario_id=scenario['id'], split=scenario['split'],
                  seed=seed, episode_index=episode, role=args.role, side=side,
                  schema='lab-teacher-v1/vcmi-v15', map_sha256=scenario['sha256'],
                  teacher='VCMI BattleAI BattleEvaluator.selectStackAction; original strength ratio and difficulty horizon; no magic/retreat/war machines',
                  engine_commit='e956242503f465ae6ec0a62a3aeb2c4ea179db5c',
                  decisions=decisions, terminal_outcome=outcome,
                  outcome_value=1.0 if outcome['winner'] == side else -1.0)
    destination = folder / (battle_id + '.npz')
    np.savez_compressed(destination, **arrays)
    record['archive_sha256'] = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix('.json').write_text(json.dumps(record, indent=2))
    all_records.append(dict(battle_id=battle_id, steps=len(decisions), winner=outcome['winner']))
print(json.dumps(dict(scenario=scenario['id'], role=args.role, elapsed_seconds=time.monotonic()-started,
                      episodes=all_records)), flush=True)
env.close()
