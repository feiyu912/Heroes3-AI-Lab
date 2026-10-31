import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import time
import numpy as np
from observation_digest import update as update_digest
from vcmi_gym.envs.v15.vcmi_env import Action, ACTION_TYPES, Unit, Global

spec = importlib.util.spec_from_file_location('lab_env', Path(__file__).with_name('lab-env.py'))
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)
parser = argparse.ArgumentParser()
parser.add_argument('--scenario', type=int, required=True)
parser.add_argument('--role', choices=['attacker', 'defender'], required=True)
parser.add_argument('--seed', type=int, required=True)
parser.add_argument('--policy', choices=['model', 'recovered', 'upstream', 'teacher', 'heuristic', 'random'], required=True)
parser.add_argument('--checkpoint')
parser.add_argument('--output', required=True)
parser.add_argument('--scenarios', default='/mnt/g/Heroes3-AI-Lab/research/scenarios-v1.json')
parser.add_argument('--opponent', default='BattleAI')
parser.add_argument('--opponent-model')
parser.add_argument('--teacher-turns', type=int, default=2)
args = parser.parse_args()
model = None
upstream = None
recovered = None
if args.policy == 'recovered':
    import torch
    torch.set_num_threads(1)
    recovered_spec=importlib.util.spec_from_file_location('recovered_graph',Path(__file__).with_name('recovered-graph.py'))
    recovered_module=importlib.util.module_from_spec(recovered_spec);recovered_spec.loader.exec_module(recovered_module)
    recovered=recovered_module.RecoveredPair(args.checkpoint).eval().models[args.role]
if args.policy == 'upstream':
    upstream_spec = importlib.util.spec_from_file_location('upstream_policy', Path(__file__).with_name('upstream-policy.py'))
    upstream_module = importlib.util.module_from_spec(upstream_spec)
    upstream_spec.loader.exec_module(upstream_module)
    upstream = upstream_module.UpstreamPolicy(args.checkpoint)
    assert upstream.side == int(args.role == 'defender')
if args.policy == 'model':
    import torch
    from decision_model import features, linked_features, collate, load_model
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    model, checkpoint = load_model(args.checkpoint)
    if model.architecture == 'linked-gnn':
        features = linked_features
scenario = json.loads(Path(args.scenarios).read_text())[args.scenario]
import os
os.environ['LAB_BATTLEAI_TEACHER_TURNS'] = str(args.teacher_turns)
os.environ['LAB_RANDOM_POLICY_SEED'] = str(args.seed + 100000)
env = lab.make_env(scenario['map'], args.seed, args.role, opponent=args.opponent, opponent_model=args.opponent_model)
obs, _ = env.reset()
term = trunc = False
rng = np.random.default_rng(args.seed)
latencies, actions = [], []
teacher_latencies = []
started = time.monotonic()
invalid = 0
import hashlib
trajectory_digest = hashlib.sha256()
while not (term or trunc):
    ids = np.asarray(obs['active_action_ids'])
    update_digest(trajectory_digest,obs)
    before = time.perf_counter()
    if model is not None:
        inputs = features(obs)
        with torch.inference_mode():
            logits, value = model(*collate([inputs]))
            assert torch.isfinite(logits).all() and torch.isfinite(value).all()
            action = int(inputs[3][int(logits.argmax())])
    elif recovered is not None:
        with torch.inference_mode():
            logits,value=recovered(obs)
            action=int(ids[int(logits.argmax())])
    elif upstream is not None:
        action, _, _ = upstream.predict(obs)
    elif args.policy == 'teacher':
        action = int(obs['teacher_action_id'])
        import re
        timing = re.search(r'teacher_eval_us=(\d+)', obs['teacher_action_description'])
        if timing:
            teacher_latencies.append(int(timing.group(1)) / 1000)
    elif args.policy == 'random':
        action = int(rng.choice(ids))
    else:
        priority = {ACTION_TYPES[name]: rank for rank, name in
                    enumerate(['SHOOT', 'AMOVE', 'MOVE', 'DEFEND', 'WAIT'])}
        decoded = Action.decode_many(obs['nodes']['Action'][ids])
        action = min(zip(ids.tolist(), decoded), key=lambda p: (priority[p[1].ACTION_TYPE], p[0]))[0]
    latencies.append((time.perf_counter() - before) * 1000)
    if action not in ids:
        invalid += 1
        raise RuntimeError(f'Illegal action {action}')
    actions.append(int(Action.decode_one(obs['nodes']['Action'][action]).ACTION_TYPE))
    obs, _, term, trunc, info = env.step(action)
outcome = obs.get('terminal_outcome')
side = int(args.role == 'defender')
result = dict(scenario=scenario['id'], split=scenario['split'], role=args.role, seed=args.seed,
              opponent=args.opponent, opponent_model=args.opponent_model, engine_seed=args.seed,
              opponent_seed=args.seed+100000 if args.opponent=='MMAI_RANDOM' else (args.seed if args.opponent=='MMAI_MODEL' else None),
              opponent_temperature=0 if args.opponent=='MMAI_MODEL' else None,
              policy=args.policy, checkpoint=args.checkpoint, steps=len(actions),
              terminated=bool(term), truncated=bool(trunc), invalid_actions=invalid,
              success=bool(term and not trunc and outcome and outcome['result_type'] == 0 and outcome['winner'] == side),
              terminal_outcome=outcome, action_types=dict(Counter(actions)),
              trajectory_sha256=trajectory_digest.hexdigest(),
              trajectory_hash_version=2,
              wall_seconds=time.monotonic()-started,
              policy_latency_ms=dict(zip(['p50', 'p95', 'p99'], np.percentile(latencies, [50, 95, 99]).tolist())))
if teacher_latencies:
    result['teacher_engine_latency_ms'] = dict(zip(['p50', 'p95', 'p99'], np.percentile(teacher_latencies, [50, 95, 99]).tolist()))
    result['teacher_python_selection_latency_only'] = True
if trunc and not term:
    result['failure_final_round'] = int(Global.decode_one(obs['nodes']['Global'][0]).BATTLE_ROUND)
    result['failure_units'] = [{name: int(getattr(unit, name)) for name in
                               ['IS_ENEMY', 'SHOTS', 'IS_SLEEPING', 'HAS_FLYING', 'HAS_BIND', 'VALUE_REL']}
                              for unit in Unit.decode_many(obs['nodes']['Unit'])]
Path(args.output).write_text(json.dumps(result, indent=2))
print(json.dumps(result), flush=True)
env.close()
