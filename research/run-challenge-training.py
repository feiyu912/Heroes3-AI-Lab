"""Bounded continued PPO, checkpoint selection exclusively on validation battles."""
import json
import os
from pathlib import Path
import subprocess

root=Path('/mnt/g/Heroes3-AI-Lab'); r=root/'research'
python='/root/heroes3-ai-lab/gpu-venv/bin/python'
initial=json.loads((r/'linked-model-initialization.json').read_text())['checkpoint']
baseline=json.loads((r/'selected-trained-model.json').read_text())
results=[]

def evaluate(checkpoint,name,opponent='BattleAI',cases=range(20,26),seeds=4):
    output=r/(name+'.json')
    command=['python3',str(r/'evaluate-battles.py'),'--checkpoint',checkpoint,'--policies','model',
             '--scenario-file',str(r/'scenarios-v2.json'),'--scenarios',*map(str,cases),
             '--seeds',str(seeds),'--workers','12','--opponent',opponent,'--output',str(output)]
    if opponent=='MMAI_MODEL':
        command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
    with (r/(name+'.log')).open('wb') as log:
        subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    return str(output),json.loads(output.read_text())['summary'][0]

initial_validation,_=evaluate(initial,'linked-v4-initial-validation')
for name,checkpoint,validation,updates,opponents,resume in [
    ('linked-v4-battleai',initial,initial_validation,512,['BattleAI'],False),
    ('unlinked-v4-battleai',baseline['checkpoint'],baseline['validation_report'],512,['BattleAI'],True),
]:
    output=r/(name+'.json')
    command=['bash',str(r/'run-lab.sh'),str(r/'train-ppo.py'),'--workers','12','--rollout','64',
             '--updates',str(updates),'--epochs','3','--batch-size','64','--seed','20261015',
             '--checkpoint',checkpoint,'--validation-report',validation,'--scenarios',str(r/'scenarios-v2.json'),
             '--inference-device','cuda','--training-device','cuda','--cache-next-value','--rotate-every','32',
             '--opponents',*opponents,'--output',str(output)]
    if resume: command+=['--resume']
    with (r/(name+'.log')).open('wb') as log:
        subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=7200,
                       env=dict(os.environ,LAB_PYTHON=python))
    data=json.loads(output.read_text()); assert data['completed'] and data['all_workers_exit_zero']
    folder=Path(data['checkpoint']).parent
    prior=data['resumed_from_updates']
    for iteration in [128,256,512]:
        path=data['checkpoint'] if iteration==512 else str(folder/f'update-{prior+iteration}.pt')
        report,summary=evaluate(path,f'{name}-update{iteration}-validation')
        results.append(dict(name=name,iteration=iteration,checkpoint=path,validation_report=report,validation=summary))
        (r/'challenge-training-progress.json').write_text(json.dumps(results,indent=2))
    print(name,'completed',flush=True)

best=max(results,key=lambda x:(x['validation']['win_rate'],-x['validation']['mean_permanent_units_lost']))
mixed_output=r/'challenge-mixed-v4.json'
command=['bash',str(r/'run-lab.sh'),str(r/'train-ppo.py'),'--workers','12','--rollout','64',
         '--updates','128','--epochs','3','--batch-size','64','--seed','20261016',
         '--checkpoint',best['checkpoint'],'--validation-report',best['validation_report'],
         '--scenarios',str(r/'scenarios-v2.json'),'--inference-device','cuda','--training-device','cuda',
         '--cache-next-value','--rotate-every','32','--opponents','BattleAI','MMAI_MODEL',
         '--output',str(mixed_output)]
with (r/'challenge-mixed-v4.log').open('wb') as log:
    process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=7200,
                           env=dict(os.environ,LAB_PYTHON=python))
if process.returncode == 0:
    data=json.loads(mixed_output.read_text());assert data['completed'] and data['all_workers_exit_zero']
    report,summary=evaluate(data['checkpoint'],'challenge-mixed-v4-validation')
    results.append(dict(name='challenge-mixed-v4',iteration=128,checkpoint=data['checkpoint'],validation_report=report,validation=summary))
else:
    (r/'challenge-mixed-v4-failure.json').write_text(json.dumps(dict(returncode=process.returncode,
        excluded=True,reason='Training guard failed; full log retained; no failed run accepted as a model'),indent=2))
for row in results:
    report,summary=evaluate(row['checkpoint'],row['name']+'-update'+str(row['iteration'])+'-vs-upstream-validation',opponent='MMAI_MODEL')
    row.update(upstream_validation_report=report,upstream_validation=summary)
(r/'challenge-training-progress.json').write_text(json.dumps(results,indent=2))
best=max(results,key=lambda x:(min(x['validation']['win_rate'],x['upstream_validation']['win_rate']),
                              x['validation']['win_rate']+x['upstream_validation']['win_rate'],
                              -x['validation']['mean_permanent_units_lost']))
best['selection']='Validation only: maximize lower of BattleAI and upstream win rates, then sum, then lower BattleAI casualties; no test selection'
(r/'challenge-selected-model.json').write_text(json.dumps(best,indent=2))
for opponent,label in [('BattleAI','battleai'),('MMAI_MODEL','upstream')]:
    report,summary=evaluate(best['checkpoint'],'challenge-selected-vs-'+label,cases=range(26,36),seeds=8,opponent=opponent)
    print(label,summary,flush=True)
print('CHALLENGE TRAINING AND MATCHED EVALUATION COMPLETE',flush=True)
