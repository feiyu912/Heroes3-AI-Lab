"""Select on both opponents' validation results, including untouched baselines."""
import json
from pathlib import Path
import subprocess
import time

r=Path('/mnt/g/Heroes3-AI-Lab/research')
control=r/'goal-v5-control.json'
while control.exists():
    try:state=json.loads(control.read_text())
    except json.JSONDecodeError:
        time.sleep(1);continue
    if state['state']=='experiments_complete':break
    if state['state']=='failed':raise RuntimeError('Extended goal experiments failed; inspect goal-v5 logs')
    time.sleep(15)
rows=json.loads((r/'challenge-training-progress.json').read_text())
rows+=json.loads((r/'recovered-adaptation-validation.json').read_text())
initial='/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt'
row=dict(name='upstream-v15-unmodified',policy='recovered',iteration=0,checkpoint=initial)
for opponent,label in [('BattleAI','battleai'),('MMAI_MODEL','upstream')]:
    output=r/('upstream-unmodified-'+label+'-validation.json')
    command=['python3',str(r/'evaluate-battles.py'),'--checkpoint',initial,'--policies','recovered',
        '--scenario-file',str(r/'scenarios-v2.json'),'--scenarios',*map(str,range(20,26)),
        '--seeds','4','--workers','12','--opponent',opponent,'--output',str(output)]
    if opponent=='MMAI_MODEL':command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
    with output.with_suffix('.log').open('wb') as log:
        subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    prefix='' if label=='battleai' else 'upstream_'
    row[prefix+'validation_report']=str(output);row[prefix+'validation']=json.loads(output.read_text())['summary'][0]
rows.append(row)
for row in rows:row.setdefault('policy','model')
best=max(rows,key=lambda x:(min(x['validation']['win_rate'],x['upstream_validation']['win_rate']),
    x['validation']['win_rate']+x['upstream_validation']['win_rate'],-x['validation']['mean_permanent_units_lost']))
best['selection']='Only validation: maximize worst of BattleAI/upstream win rates, then sum, then lower casualties; original lab and original upstream also included'
if (r/'goal-v5-selection.json').exists():
    rows+=json.loads((r/'goal-v5-validation.json').read_text())
    best=json.loads((r/'goal-v5-selection.json').read_text())
(r/'challenge-final-selection.json').write_text(json.dumps(best,indent=2))
(r/'challenge-all-validation.json').write_text(json.dumps(rows,indent=2))
print(best,flush=True)
