import argparse
from collections import Counter
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import time
import fcntl
import shutil
from lab_io import atomic_json
from evaluation_provenance import freeze,verify

parser = argparse.ArgumentParser()
parser.add_argument('--checkpoint', default='/root/heroes3-ai-lab/models/bc-v1/mlp.pt')
parser.add_argument('--policies', nargs='+', default=['teacher', 'heuristic', 'model'])
parser.add_argument('--scenarios', nargs='+', type=int, default=[10, 11])
parser.add_argument('--seeds', type=int, default=5)
parser.add_argument('--seed-base',type=int,default=2026103400)
parser.add_argument('--workers', type=int, default=12)
parser.add_argument('--output', default='/mnt/g/Heroes3-AI-Lab/research/battle-evaluation-v1.json')
parser.add_argument('--scenario-file', default='/mnt/g/Heroes3-AI-Lab/research/scenarios-v1.json')
parser.add_argument('--opponent', default='BattleAI')
parser.add_argument('--opponent-model-dir')
parser.add_argument('--opponent-model-template')
parser.add_argument('--upstream-model-dir', default='/mnt/g/Heroes3-AI-Lab/models/upstream-v15')
parser.add_argument('--teacher-turns', type=int, default=2)
parser.add_argument('--force',action='store_true',help='Archive and rerun an existing evaluation')
args = parser.parse_args()
pool_lock=Path('/root/heroes3-ai-lab/evaluations/.pool-lock')
pool_lock.parent.mkdir(parents=True,exist_ok=True)
lock_stream=pool_lock.open('a')
fcntl.flock(lock_stream,fcntl.LOCK_EX)
frozen=freeze(args)
frozen[str(Path(__file__).resolve())]=__import__('hashlib').sha256(Path(__file__).read_bytes()).hexdigest()
if Path(args.output).exists():
    prior=json.loads(Path(args.output).read_text())
    expected=len(args.scenarios)*2*args.seeds*len(args.policies)
    if (not args.force and prior.get('checkpoint')==args.checkpoint and prior.get('scenario_file')==args.scenario_file
        and prior.get('scenario_ids')==args.scenarios and prior.get('opponent')==args.opponent
        and prior.get('teacher_turns')==args.teacher_turns
        and prior.get('opponent_model_template')==args.opponent_model_template
        and prior.get('opponent_model_dir')==args.opponent_model_dir
        and prior.get('upstream_model_dir')==args.upstream_model_dir
        and [s['policy'] for s in prior['summary']]==args.policies and len(prior['battles'])==expected
        and (not prior.get('frozen_artifacts') or prior['frozen_artifacts']==frozen)):
        print('Reusing completed matching evaluation',args.output,flush=True)
        raise SystemExit(0)
    Path(args.output).rename(args.output+'.previous-'+str(time.time_ns()))
run_id = str(time.time_ns())
folder = Path('/root/heroes3-ai-lab/evaluations') / run_id
folder.mkdir(parents=True)
protocol_folder=folder/'protocol'
protocol_folder.mkdir()
for name in frozen:
    path=Path(name)
    if path.parent==Path(__file__).parent and path.suffix in ['.py','.sh']:
        shutil.copyfile(path,protocol_folder/path.name)
started = time.monotonic()


def run(item):
    scenario, role, seed, policy = item
    name = f'{scenario}-{role}-{seed}-{policy}'
    env = dict(os.environ, LAB_BATTLEAI_TEACHER='1' if policy == 'teacher' else '0',
               LAB_WORKER_ROOT=f'/root/heroes3-ai-lab/workers/eval-{run_id}/{name}')
    output = folder / (name + '.json')
    with (folder / (name + '.log')).open('wb') as stream:
        checkpoint = str(Path(args.upstream_model_dir) / (role + '.onnx')) if policy == 'upstream' else args.checkpoint
        extra = []
        if args.opponent_model_dir or args.opponent_model_template:
            opposite = 'defender' if role == 'attacker' else 'attacker'
            path = args.opponent_model_template.format(role=opposite) if args.opponent_model_template else str(Path(args.opponent_model_dir) / (opposite + '.onnx'))
            extra = ['--opponent-model', path]
        result = subprocess.run(['bash', '/mnt/g/Heroes3-AI-Lab/research/run-lab.sh',
                                 '/mnt/g/Heroes3-AI-Lab/research/evaluate-policy.py',
                                 '--scenario', str(scenario), '--role', role, '--seed', str(seed),
                                 '--policy', policy, '--checkpoint', checkpoint,
                                 '--output', str(output), '--scenarios', args.scenario_file,
                                 '--opponent', args.opponent, '--teacher-turns', str(args.teacher_turns), *extra], env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=300)
    assert result.returncode == 0, f'{name}: see {folder / (name + ".log")}'
    return json.loads(output.read_text())


jobs = [(scenario, role, args.seed_base + scenario * 100 + seed, policy)
        for scenario in args.scenarios for role in ['attacker', 'defender']
        for seed in range(args.seeds) for policy in args.policies]
with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
    records = list(pool.map(run, jobs))
summary = []
for policy in args.policies:
    rows = [r for r in records if r['policy'] == policy]
    wins = sum(r['success'] for r in rows)
    n = len(rows)
    p = wins / n
    z = 1.96
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    half = z * ((p*(1-p)/n + z*z/(4*n*n)) ** 0.5) / (1 + z*z/n)
    casualties = []
    for r in rows:
        if r['terminated'] and not r['truncated'] and r['terminal_outcome']['result_type'] == 0:
            side = int(r['role'] == 'defender')
            casualties.append(sum(r['terminal_outcome']['casualties'][str(side)].values()))
    summary.append(dict(policy=policy, battles=n, wins=wins, win_rate=p,
                        wilson95=[center-half, center+half],
                        truncated=sum(r['truncated'] for r in rows),
                        non_normal_terminations=sum(r['terminated'] and r['terminal_outcome']['result_type']!=0 for r in rows),
                        invalid_actions=sum(r['invalid_actions'] for r in rows),
                        mean_permanent_units_lost=sum(casualties)/len(casualties) if casualties else None))
output = dict(run_id=run_id, workers=args.workers, checkpoint=args.checkpoint,
               opponent=args.opponent, opponent_model_dir=args.opponent_model_dir,
               opponent_model_template=args.opponent_model_template,
               upstream_model_dir=args.upstream_model_dir, teacher_turns=args.teacher_turns, scenario_file=args.scenario_file,
               independent_battle_seed=True, scenario_ids=args.scenarios,
               wall_seconds=time.monotonic()-started, summary=summary, battles=records)
verify(frozen)
output.update(frozen_artifacts=frozen,artifacts_checked_before_and_after=True,protocol_snapshot=str(protocol_folder))
atomic_json(args.output,output)
print(json.dumps(summary), flush=True)
