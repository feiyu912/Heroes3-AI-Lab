import json
import os
from pathlib import Path
import subprocess
import torch

r=Path('/mnt/g/Heroes3-AI-Lab/research')
partial=json.loads((r/'unlinked-v4-partial-12.json').read_text())
checkpoint=partial['checkpoint']
state=torch.load(checkpoint,map_location='cpu',weights_only=True)
already=state['completed_updates']-partial['resumed_from_updates']
remaining=512-already
assert 0<remaining<=512
def evaluate(path,name):
    output=r/(name+'.json')
    command=['python3',str(r/'evaluate-battles.py'),'--checkpoint',path,'--policies','model',
        '--scenario-file',str(r/'scenarios-v2.json'),'--scenarios',*map(str,range(20,26)),
        '--seeds','4','--workers','12','--output',str(output)]
    with output.with_suffix('.log').open('wb') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    return str(output),json.loads(output.read_text())['summary'][0]
validation,_=evaluate(checkpoint,'unlinked-v4-partial-validation')
output=r/'unlinked-v4-battleai.json'
command=['bash',str(r/'run-lab.sh'),str(r/'train-ppo.py'),'--workers','24','--rollout','32',
    '--updates',str(remaining),'--epochs','3','--batch-size','64','--seed','20261015','--resume',
    '--checkpoint',checkpoint,'--validation-report',validation,'--scenarios',str(r/'scenarios-v2.json'),
    '--inference-device','cuda','--training-device','cuda','--cache-next-value','--rotate-every','32','--output',str(output)]
with output.with_suffix('.log').open('wb') as log:
    subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=7200,
        env=dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',LAB_STAGED_BOOT='1'))
data=json.loads(output.read_text());assert data['completed'] and data['all_workers_exit_zero']
results=json.loads((r/'challenge-training-progress.json').read_text());assert len(results)==3
folder=Path(data['checkpoint']).parent
iterations=sorted(set([16,max(16,16*(remaining//2//16)),remaining]))
for iteration in iterations:
    path=data['checkpoint'] if iteration==remaining else str(folder/f"update-{state['completed_updates']+iteration}.pt")
    report,summary=evaluate(path,f'unlinked-v4-battleai-update{already+iteration}-validation')
    results.append(dict(name='unlinked-v4-battleai',iteration=already+iteration,checkpoint=path,
        validation_report=report,validation=summary,workers=24,
        limitation='First '+str(already)+' updates at12/roll64, continued at24/roll32; equal total samples, not an architecture-only control'))
    (r/'challenge-training-progress.json').write_text(json.dumps(results,indent=2))
(r/'unlinked-v4-budget.json').write_text(json.dumps(dict(initial_updates12=already,continued_updates24=remaining,
    new_samples=(already+remaining)*768,completed=True),indent=2))
print('24-worker continuation completed, six validation candidates ready',flush=True)
