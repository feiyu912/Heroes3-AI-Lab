import json
import os
from pathlib import Path
import subprocess

root = Path('/mnt/g/Heroes3-AI-Lab/research')
outputs = []
for repeat in range(2):
    output = root / f'random-replay-{repeat}.json'
    subprocess.run(['bash', str(root / 'run-lab.sh'), str(root / 'evaluate-policy.py'),
                    '--scenario', '26', '--role', 'attacker', '--seed', '2026101403',
                    '--policy', 'teacher', '--opponent', 'MMAI_RANDOM',
                    '--scenarios', str(root / 'scenarios-v2.json'), '--output', str(output)],
                   env=dict(os.environ, LAB_BATTLEAI_TEACHER='1',
                            LAB_WORKER_ROOT=f'/root/heroes3-ai-lab/workers/random-replay-{repeat}'),
                   check=True, timeout=60)
    outputs.append(json.loads(output.read_text()))
fields = ['trajectory_sha256', 'terminal_outcome', 'steps', 'action_types', 'success', 'truncated', 'terminated']
assert all(outputs[0][key] == outputs[1][key] for key in fields), 'Random opponent replay differs'
assert outputs[0]['terminated'] and not outputs[0]['truncated']
(root / 'random-opponent-replay.json').write_text(json.dumps(dict(passed=True,
    engine_seed=2026101403, opponent_seed=2026201403, checked_fields=fields,
    trajectory_sha256=outputs[0]['trajectory_sha256']), indent=2))
print('Seeded random opponent independent replay passed')
