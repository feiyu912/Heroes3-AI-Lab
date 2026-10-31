from pathlib import Path
import json
import subprocess
import uuid

root = Path(__file__).resolve().parent
manifest = []
for label, role in [('attacker-1', 'attacker'), ('attacker-2', 'attacker'),
                    ('defender-1', 'defender')]:
    output = '/mnt/g/Heroes3-AI-Lab/research/smoke-' + label + '.json'
    run_id = str(uuid.uuid4())
    result = subprocess.run(['wsl.exe', '-d', 'Ubuntu-22.04', '--', 'bash',
                             '/mnt/g/Heroes3-AI-Lab/research/run-battle-smoke.sh',
                             '--role', role, '--episodes', '5', '--output', output, '--run-id', run_id],
                            capture_output=True, timeout=45)
    (root / ('smoke-' + label + '.log')).write_bytes(result.stdout + result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f'{label}: worker exited {result.returncode}; see log')
    data = json.loads((root / ('smoke-' + label + '.json')).read_text())
    assert data['completed'] and data['run_id'] == run_id, 'Stale or incomplete result artifact'
    assert len(data['episodes']) == 5
    assert all(e['terminated'] and not e['truncated'] for e in data['episodes'])
    assert all(e['steps'] > 0 for e in data['episodes'])
    manifest.append({'run': label, 'exit_code': result.returncode, 'role': role,
                     'episodes': len(data['episodes']),
                     'decisions': sum(e['steps'] for e in data['episodes'])})
    print(manifest[-1], flush=True)

first = json.loads((root / 'smoke-attacker-1.json').read_text())
second = json.loads((root / 'smoke-attacker-2.json').read_text())
for a, b in zip(first['episodes'], second['episodes']):
    assert a == b, 'Fixed-seed independent-process replay diverged'
summary = {'passed': True, 'runs': manifest,
           'same_seed_independent_process_replay': True,
           'total_episodes': sum(r['episodes'] for r in manifest),
           'total_decisions': sum(r['decisions'] for r in manifest),
           'scope': 'Fixed no-magic archer battle, schema v15, legal diagnostic policy vs BattleAI'}
(root / 'smoke-verification.json').write_text(json.dumps(summary, indent=2))
print(json.dumps(summary), flush=True)
