"""Read-only compact snapshot; absent reports are not completed games."""
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
result = root / 'RESULT.json'
if result.exists():
    print(json.dumps({'result': json.loads(result.read_text())}))
else:
    reports = []
    for name in ('B64', 'update30'):
        for opponent in ('BattleAI', 'MMAI_MODEL'):
            path = root / f'{name}-{opponent}-DEV.json'
            if path.exists():
                data = json.loads(path.read_text())
                reports.append({'model': name, 'opponent': opponent,
                                'summary': data.get('summary'),
                                'completed': data.get('completed')})
    print(json.dumps({'pipeline_completed': False, 'reports': reports}))
