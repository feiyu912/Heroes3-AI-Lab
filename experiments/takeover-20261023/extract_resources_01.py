"""Print post-update resource rows already recorded in stage RESULT files."""
import json
from pathlib import Path

RUN = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-native-20261023-01')
for name in ['qualification', 'control-micro', 'candidate-micro', 'control-phase-1']:
    path = RUN / name / 'RESULT.json'
    d = json.loads(path.read_text())
    print('==', name, '==')
    print('stage resources:', json.dumps(d.get('resources')))
    for record in d.get('records', []):
        print('update', record.get('update'), 'half', record.get('half'),
              'resources', json.dumps(record.get('resources')))
