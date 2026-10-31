import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument('--dataset', default='/root/heroes3-ai-lab/datasets/teacher-v1')
parser.add_argument('--episodes', type=int, default=10)
parser.add_argument('--workers', type=int, default=12)
parser.add_argument('--scenarios', default='/mnt/g/Heroes3-AI-Lab/research/scenarios-v1.json')
args = parser.parse_args()
root = Path(args.dataset)
root.mkdir(parents=True, exist_ok=True)
assert not list(root.rglob('*.npz')), 'Use a fresh dataset directory'
started = time.monotonic()
scenarios = json.loads(Path(args.scenarios).read_text())
run_id = str(time.time_ns())


def run(item):
    i, role = item
    log = root / f'collect-{i}-{role}.log'
    env = dict(os.environ, LAB_BATTLEAI_TEACHER='1',
               LAB_WORKER_ROOT=f'/root/heroes3-ai-lab/workers/teacher-{run_id}/{i}-{role}')
    with log.open('wb') as stream:
        result = subprocess.run(['bash', '/mnt/g/Heroes3-AI-Lab/research/run-lab.sh',
                                 '/mnt/g/Heroes3-AI-Lab/research/collect-teacher.py',
                                 '--scenario', str(i), '--role', role, '--episodes', str(args.episodes),
                                 '--dataset', str(root), '--scenarios', args.scenarios], env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=240)
    assert result.returncode == 0, f'{item}: see {log}'
    return i, role


with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
    for result in pool.map(run, [(i, role) for i in range(len(scenarios))
                                for role in ['attacker', 'defender']]):
        print('COLLECTED', result, flush=True)

records = [json.loads(p.read_text()) for p in root.rglob('*.json') if 'battle_id' in json.loads(p.read_text())]
hashes = {s: set() for s in ['train', 'validation', 'test']}
types = Counter()
for record in records:
    hashes[record['split']].update(d['observation_sha256'] for d in record['decisions'])
    types.update(d['action_type'] for d in record['decisions'])
overlap = {f'{a}/{b}': len(hashes[a] & hashes[b]) for a, b in
           [('train', 'validation'), ('train', 'test'), ('validation', 'test')]}
assert not any(overlap.values()), f'Exact observation leakage: {overlap}'
summary = dict(dataset=str(root), run_id=run_id, schema='lab-teacher-v1/vcmi-v15',
               episodes=len(records), steps=sum(len(r['decisions']) for r in records),
               splits={s: dict(battles=sum(r['split'] == s for r in records),
                               steps=sum(len(r['decisions']) for r in records if r['split'] == s),
                               unique_states=len(hashes[s])) for s in hashes},
               action_types=dict(types), exact_state_overlap=overlap,
               failures=len(list(root.rglob('*.failure.json'))),
               wall_seconds=time.monotonic()-started, workers=args.workers,
               teacher_patch_sha256=hashlib.sha256(Path('/mnt/g/Heroes3-AI-Lab/research/teacher-interface.patch').read_bytes()).hexdigest())
(root / 'manifest.json').write_text(json.dumps(summary, indent=2))
Path('/mnt/g/Heroes3-AI-Lab/research/teacher-quality-v1.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary), flush=True)
