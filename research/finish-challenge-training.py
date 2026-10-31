import json,os,subprocess
from pathlib import Path
root=Path('/mnt/g/Heroes3-AI-Lab');r=root/'research'
python='/root/heroes3-ai-lab/gpu-venv/bin/python'
results=json.loads((r/'challenge-training-progress.json').read_text())
assert len(results)==6
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
best=max(results,key=lambda x:(x['validation']['win_rate'],-x['validation']['mean_permanent_units_lost']))
mixed_output=r/'challenge-mixed-v4.json'
capacity=json.loads((r/'challenge-concurrency-results.json').read_text())
assert capacity['completed']
workers=capacity['recommended_workers']
updates=__import__('math').ceil(98304/(workers*32))
command=['bash',str(r/'run-lab.sh'),str(r/'train-ppo.py'),'--workers',str(workers),'--rollout','32',
         '--updates',str(updates),'--epochs','3','--batch-size','64','--seed','20261016',
         '--checkpoint',best['checkpoint'],'--validation-report',best['validation_report'],
         '--scenarios',str(r/'scenarios-v2.json'),'--inference-device','cuda','--training-device','cuda',
         '--cache-next-value','--rotate-every','32','--opponents','BattleAI','MMAI_MODEL',
         '--output',str(mixed_output)]
with (r/'challenge-mixed-v4.log').open('wb') as log:
    process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=7200,
                           env=dict(os.environ,LAB_PYTHON=python,LAB_STAGED_BOOT='1'))
if process.returncode == 0:
    data=json.loads(mixed_output.read_text());assert data['completed'] and data['all_workers_exit_zero']
    report,summary=evaluate(data['checkpoint'],'challenge-mixed-v4-validation')
    results.append(dict(name='challenge-mixed-v4',iteration=updates,checkpoint=data['checkpoint'],validation_report=report,validation=summary))
else:
    (r/'challenge-mixed-v4-failure.json').write_text(json.dumps(dict(returncode=process.returncode,
        excluded=True,reason='Training guard failed; full log retained; no failed run accepted as a model'),indent=2))
baseline=json.loads((r/'selected-trained-model.json').read_text())
baseline_validation=json.loads(Path(baseline['validation_report']).read_text())['summary'][0]
results.append(dict(name='lab-v3-original',iteration=0,checkpoint=baseline['checkpoint'],
                    validation_report=baseline['validation_report'],validation=baseline_validation))
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
