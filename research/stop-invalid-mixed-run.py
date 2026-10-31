"""Stop only the known lab mixed-opponent experiment tree and preserve evidence."""
from pathlib import Path
import json
import os
import signal
import time

roots = [299, 38677]
assert not Path('/mnt/g/Heroes3-AI-Lab/research/random-opponent-invalid-run.json').exists(), 'One-time diagnostic already completed; do not stop new experiments'
expected = ['run-ppo-research-suite.py', 'ppo-balanced-mixed.json']
live_roots = []
for pid, marker in zip(roots, expected):
    path = Path(f'/proc/{pid}/cmdline')
    if not path.exists():
        continue
    command = path.read_bytes().replace(b'\0', b' ').decode()
    assert marker in command, f'PID changed: {pid}'
    live_roots.append(pid)
parents = {}
for status in Path('/proc').glob('[0-9]*/status'):
    try:
        fields = dict(line.split(':', 1) for line in status.read_text().splitlines() if ':' in line)
        parents[int(status.parent.name)] = int(fields['PPid'])
    except (FileNotFoundError, ProcessLookupError):
        pass
targets = set(live_roots)
while True:
    expanded = targets | {pid for pid, parent in parents.items() if parent in targets}
    if expanded == targets:
        break
    targets = expanded
for pid in sorted(targets - {os.getpid()}, reverse=True):
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
time.sleep(1)
for pid in targets:
    if Path(f'/proc/{pid}').exists():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
folder = Path('/mnt/g/Heroes3-AI-Lab/research')
for suffix in ['.json', '.log', '-validation.json', '-test.json']:
    source = folder / f'ppo-balanced-mixed{suffix}'
    if source.exists():
        source.rename(folder / f'ppo-balanced-mixed-unseeded-excluded{suffix}')
suite = folder / 'ppo-research-suite.json'
if suite.exists():
    records = json.loads(suite.read_text())
    suite.write_text(json.dumps([r for r in records if r['name'] != 'ppo-balanced-mixed'], indent=2))
(folder / 'random-opponent-invalid-run.json').write_text(json.dumps(dict(
    excluded=True, reason='Native MMAI_RANDOM used random_device each action; original mixed experiment excluded and will rerun from BC with a seeded generator',
    terminated_lab_pids=sorted(targets)), indent=2))
print('Stopped known lab experiment and preserved excluded partial results')
