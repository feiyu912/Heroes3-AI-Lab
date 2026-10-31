"""Independent mirror suite after policy selection; all armies and seeds held fixed."""
import json
import hashlib
from pathlib import Path
import subprocess

r=Path('/mnt/g/Heroes3-AI-Lab/research')
selection=json.loads((r/'challenge-final-selection.json').read_text())
selected=selection['checkpoint'];policy=selection['policy']
def verify_frozen_selection():
    if (r/'post-training-candidates-plan.json').exists():
        frozen=json.loads((r/'final-policy-freeze.json').read_text())
        assert frozen['name']==selection['name'] and frozen['policy']==selection['policy']
        assert frozen['source_checkpoint']==selected
        digest=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
        assert digest(selected)==frozen['sha256']==digest(frozen['backup_checkpoint'])
verify_frozen_selection()
previous=json.loads((r/'selected-trained-model.json').read_text())['checkpoint']
jobs=[('fresh-upstream-vs-battleai','upstream','BattleAI',selected),
      ('fresh-v3-vs-battleai','model','BattleAI',previous),
      ('fresh-selected-vs-battleai',policy,'BattleAI',selected),
      ('fresh-selected-vs-upstream',policy,'MMAI_MODEL',selected),
      ('fresh-v3-vs-upstream','model','MMAI_MODEL',previous),
      ('fresh-battleai-vs-battleai','teacher','BattleAI',selected)]
results=[]
for name,policy,opponent,checkpoint in jobs:
    verify_frozen_selection()
    command=['python3',str(r/'evaluate-battles.py'),'--checkpoint',checkpoint,'--policies',policy,
             '--scenario-file',str(r/'challenge-holdout.json'),'--scenarios',*map(str,range(32)),
             '--seeds','8','--workers','12','--opponent',opponent,'--output',str(r/(name+'.json'))]
    if opponent=='MMAI_MODEL':
        command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
    with (r/(name+'.log')).open('wb') as log:
        subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=3600)
    data=json.loads((r/(name+'.json')).read_text())
    results.append(dict(name=name,summary=data['summary'],report=str(r/(name+'.json'))))
    (r/'fresh-challenge-results.json').write_text(json.dumps(results,indent=2))
    print(name,data['summary'],flush=True)
