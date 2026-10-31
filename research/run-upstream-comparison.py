"""Same engine/cases/seeds, official v15 models vs lab policy and BattleAI."""
import json
from pathlib import Path
import subprocess

root = Path('/mnt/g/Heroes3-AI-Lab')
r = root / 'research'
selected = json.loads((r/'selected-trained-model.json').read_text())['checkpoint']
template = 'DATA/MMAI/models/lab-upstream-{role}.onnx'
jobs = [
    ('upstream-v15-vs-battleai', ['--policies', 'upstream']),
    ('lab-v3-vs-upstream-v15', ['--policies', 'model', '--opponent', 'MMAI_MODEL', '--opponent-model-template', template]),
    ('upstream-v15-vs-upstream-v15', ['--policies', 'upstream', '--opponent', 'MMAI_MODEL', '--opponent-model-template', template]),
]
results = []
for name, extra in jobs:
    command = ['python3', str(r/'evaluate-battles.py'), '--checkpoint', selected,
               '--scenario-file', str(r/'scenarios-v2.json'), '--scenarios', *map(str,range(26,36)),
               '--seeds', '8', '--workers', '12', '--output', str(r/(name+'.json')), *extra]
    with (r/(name+'.log')).open('wb') as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
    data=json.loads((r/(name+'.json')).read_text())
    results.append(dict(name=name, summary=data['summary'], report=str(r/(name+'.json'))))
    (r/'upstream-comparison-progress.json').write_text(json.dumps(results,indent=2))
    print(name,data['summary'],flush=True)
