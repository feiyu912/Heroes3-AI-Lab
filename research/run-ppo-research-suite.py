"""Bounded sequential PPO comparisons; one GPU trainer at a time."""
import json
import os
from pathlib import Path
import subprocess
import time
import argparse

folder = Path('/mnt/g/Heroes3-AI-Lab/research')
selection = json.loads((folder / 'selected-balanced-model.json').read_text())
parser = argparse.ArgumentParser()
parser.add_argument('--extra-only', action='store_true')
parser.add_argument('--mixed-and-extra', action='store_true')
parser.add_argument('--architecture-only', action='store_true')
args = parser.parse_args()
checkpoint = selection['checkpoint']
validation = selection['validation_report']
records = json.loads((folder / 'ppo-research-suite.json').read_text()) if (args.extra_only or args.mixed_and_extra or args.architecture_only) and (folder / 'ppo-research-suite.json').exists() else []
jobs = [dict(name=f'ppo-balanced-seed-{seed}', seed=seed, updates=256, extra=[])
        for seed in [20261014, 20261015, 20261016]]
# Keep ablations bounded and compare equal environment sample counts.
jobs += [dict(name='ppo-balanced-shaped', seed=20261014, updates=256, extra=['--loss-shaping', '0.05']),
         dict(name='ppo-balanced-mixed', seed=20261014, updates=256,
              extra=['--opponents', 'BattleAI', 'StupidAI', 'MMAI_RANDOM'])]
jobs += [dict(name='ppo-balanced-rollout64', seed=20261014, updates=128, extra=['--rollout', '64', '--rotate-every', '32']),
         dict(name='ppo-balanced-batch128', seed=20261014, updates=256, extra=['--batch-size', '128']),
         dict(name='ppo-balanced-epoch1', seed=20261014, updates=256, extra=['--epochs', '1'])]
if args.extra_only:
    jobs = jobs[-3:]
elif args.mixed_and_extra:
    jobs = jobs[-4:]
architecture_jobs = [dict(name='ppo-balanced-' + architecture, seed=20261014, updates=256, extra=[],
                         checkpoint=f'/mnt/g/Heroes3-AI-Lab/models/bc-balanced-v1/{architecture}.pt',
                         validation=str(folder / f'balanced-bc-{architecture}-validation.json')) for architecture in ['mlp', 'attention']]
if args.architecture_only:
    jobs = architecture_jobs
elif not (args.extra_only or args.mixed_and_extra):
    jobs += architecture_jobs
for job in jobs:
    output = folder / (job['name'] + '.json')
    log = folder / (job['name'] + '.log')
    env = dict(os.environ, LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',
               LAB_WORKER_ROOT='/root/heroes3-ai-lab/workers/suite-' + job['name'])
    command = ['bash', str(folder / 'run-lab.sh'), str(folder / 'train-ppo.py'), '--workers', '12',
               '--rollout', '32', '--updates', str(job['updates']), '--batch-size', '64', '--epochs', '3',
               '--inference-device', 'cuda', '--training-device', 'cuda', '--cache-next-value',
               '--rotate-every', '64', '--seed', str(job['seed']), '--checkpoint', job.get('checkpoint', checkpoint),
               '--validation-report', job.get('validation', validation), '--scenarios', str(folder / 'scenarios-v2.json'),
               '--output', str(output), *job['extra']]
    print('START', job['name'], flush=True)
    with log.open('wb') as stream:
        subprocess.run(command, env=env, check=True, stdout=stream, stderr=subprocess.STDOUT, timeout=1800)
    result = json.loads(output.read_text())
    assert result['completed'] and result['all_workers_exit_zero']
    for split, cases, seeds in [('validation', range(20, 26), 4), ('test', range(26, 36), 8)]:
        evaluation_path = folder / (job['name'] + f'-{split}.json')
        subprocess.run(['python3', str(folder / 'evaluate-battles.py'), '--checkpoint', result['checkpoint'],
                        '--scenario-file', str(folder / 'scenarios-v2.json'), '--scenarios', *map(str, cases),
                        '--policies', 'model', '--seeds', str(seeds), '--workers', '12',
                        '--output', str(evaluation_path)], check=True, timeout=240)
    record = dict(name=job['name'], training_report=str(output), checkpoint=result['checkpoint'],
                  validation_report=str(folder / (job['name'] + '-validation.json')),
                  test_report=str(folder / (job['name'] + '-test.json')),
                  steps=sum(r['steps'] for r in result['records']),
                  summary=json.loads((folder / (job['name'] + '-test.json')).read_text())['summary'][0])
    records.append(record)
    (folder / 'ppo-research-suite.json').write_text(json.dumps(records, indent=2))
    print('FINISHED', json.dumps(record), flush=True)
print('PPO SUITE COMPLETE', flush=True)
