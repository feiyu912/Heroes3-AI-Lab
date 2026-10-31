import json
from pathlib import Path
import subprocess
import time

folder = Path('/mnt/g/Heroes3-AI-Lab/research')
results = []
for architecture in ['mlp', 'attention', 'gnn']:
    checkpoint = f'/mnt/g/Heroes3-AI-Lab/models/bc-balanced-v1/{architecture}.pt'
    for split, cases, seeds in [('validation', range(20, 26), 4), ('test', range(26, 36), 8)]:
        output = folder / f'balanced-bc-{architecture}-{split}.json'
        command = ['python3', str(folder / 'evaluate-battles.py'), '--checkpoint', checkpoint,
                   '--scenario-file', str(folder / 'scenarios-v2.json'), '--scenarios', *map(str, cases),
                   '--policies', 'model', '--seeds', str(seeds), '--workers', '12', '--output', str(output)]
        subprocess.run(command, check=True)
        data = json.loads(output.read_text())
        results.append(dict(architecture=architecture, split=split, output=str(output), summary=data['summary'][0]))
        (folder / 'balanced-architecture-comparison.json').write_text(json.dumps(results, indent=2))
validation = [r for r in results if r['split'] == 'validation']
best = max(validation, key=lambda r: (r['summary']['win_rate'], -r['summary']['mean_permanent_units_lost']))
(folder / 'selected-balanced-model.json').write_text(json.dumps(dict(
    architecture=best['architecture'], checkpoint=f'/mnt/g/Heroes3-AI-Lab/models/bc-balanced-v1/{best["architecture"]}.pt',
    validation_report=best['output'], criterion='Validation battle win rate, ties broken by mean casualties; test not used for selection'), indent=2))
