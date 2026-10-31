"""Measure full-graph throughput, then PPO-adapt the published model heads."""
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys

r=Path('/mnt/g/Heroes3-AI-Lab/research')
python='/root/heroes3-ai-lab/gpu-venv/bin/python'
bench=[]
capacity=json.loads((r/'challenge-concurrency-results.json').read_text())
safe=max(int(k) for k in capacity['medians'])
initial='/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt'
paused=json.loads((r/'challenge-paused-state.json').read_text()) if '--resume-paused' in sys.argv else None
if paused:
    assert paused['status'] in ['paused_for_user_shutdown','checkpoint_recovery'] and paused['resume_available']
    initial=paused['checkpoint']
validation=r/'recovered-initial-live-validation.json'
command=['python3',str(r/'evaluate-battles.py'),'--checkpoint',initial,'--policies','recovered',
    '--scenario-file',str(r/'scenarios-v2.json'),'--scenarios',*map(str,range(20,26)),
    '--seeds','4','--workers','12','--output',str(validation)]
if not paused:
    with validation.with_suffix('.log').open('wb') as log:
        subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
live=json.loads(validation.read_text());assert len(live['battles'])>=20
assert all(row['terminated'] and not row['truncated'] and not row['invalid_actions'] for row in live['battles'])
for workers in ([] if paused else [24]):
    for repeat in range(2):
        output=r/f'recovered-speed-{workers}-{repeat}.json'
        command=['bash',str(r/'run-lab.sh'),str(r/'train-recovered-heads.py'),'--workers',str(workers),
            '--updates','4','--rollout','8','--checkpoint',initial,'--output',str(output)]
        with output.with_suffix('.log').open('wb') as log:
            process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1200,
                env=dict(os.environ,LAB_PYTHON=python,LAB_STAGED_BOOT='1'))
        if process.returncode:
            bench.append(dict(workers=workers,repeat=repeat,failed=True,returncode=process.returncode));break
        data=json.loads(output.read_text());assert data['completed'] and data['all_workers_exit_zero']
        bench.append(dict(workers=workers,repeat=repeat,failed=False,
            steps_per_second=statistics.median(x['steps_per_second'] for x in data['records'][1:]),
            peak_gpu_mib=max(x['gpu_allocated_mib'] for x in data['records'])))
        (r/'recovered-speed-grid.json').write_text(json.dumps(dict(results=bench,completed=False),indent=2))
valid={n:statistics.median(x['steps_per_second'] for x in bench if x['workers']==n and not x['failed'])
       for n in {x['workers'] for x in bench} if len([x for x in bench if x['workers']==n and not x['failed']])==2}
if paused:
    grid=json.loads((r/'recovered-speed-grid.json').read_text())
    bench=grid['results'];valid={int(k):v for k,v in grid['medians'].items()}
assert valid,'No safe full-graph trainer configuration passed'
best=max(valid,key=valid.get)
workers=24
(r/'recovered-speed-grid.json').write_text(json.dumps(dict(results=bench,completed=True,medians=valid,
    recommended_workers=workers,scope='Official frozen full graph encoding plus live CPU battle sampling and PPO head updates; warm first update omitted'),indent=2))
print('Recovered graph measured concurrency',workers,valid,flush=True)
updates=math.ceil(98304/(workers*32))
output=r/'recovered-adapted-v4.json'
command=['bash',str(r/'run-lab.sh'),str(r/'train-recovered-heads.py'),'--workers',str(workers),
    '--updates',str(paused['remaining_updates'] if paused else updates),'--rollout','32','--checkpoint',initial,'--opponents','BattleAI','MMAI_MODEL',
    '--output',str(output)]
if paused:command+=['--resume']
with output.with_suffix('.log').open('wb') as log:
    subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=7200,
        env=dict(os.environ,LAB_PYTHON=python,LAB_STAGED_BOOT='1'))
data=json.loads(output.read_text());assert data['completed'] and data['all_workers_exit_zero']
folder=Path(data['checkpoint']).parent
results=[]
iterations=sorted(set([16,max(16,16*(updates//2//16)),updates]))
for iteration in iterations:
    checkpoint=paused.get('saved_checkpoints',{}).get(str(iteration),paused['checkpoint'] if iteration==paused['completed_updates'] else str(folder/f'update-{iteration}.pt')) if paused else str(folder/f'update-{iteration}.pt')
    row=dict(iteration=iteration,checkpoint=checkpoint,policy='recovered',name='recovered-adapted-v4')
    for opponent,label in [('BattleAI','battleai'),('MMAI_MODEL','upstream')]:
        output=r/f'recovered-adapted-update{iteration}-{label}-validation.json'
        command=['python3',str(r/'evaluate-battles.py'),'--checkpoint',checkpoint,'--policies','recovered',
            '--scenario-file',str(r/'scenarios-v2.json'),'--scenarios',*map(str,range(20,26)),
            '--seeds','4','--workers','12','--opponent',opponent,'--output',str(output)]
        if opponent=='MMAI_MODEL':command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
        with output.with_suffix('.log').open('wb') as log:
            subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        prefix='' if label=='battleai' else 'upstream_'
        row[prefix+'validation_report']=str(output);row[prefix+'validation']=json.loads(output.read_text())['summary'][0]
    results.append(row)
    (r/'recovered-adaptation-validation.json').write_text(json.dumps(results,indent=2))
print('Recovered official model PPO adaptation completed',flush=True)
