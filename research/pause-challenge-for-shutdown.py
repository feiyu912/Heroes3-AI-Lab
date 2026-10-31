"""Stop only the identified lab pipeline and preserve a validated restart checkpoint."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import time

r = Path('/mnt/g/Heroes3-AI-Lab/research')
report = json.loads((r/'recovered-adapted-v4.json').read_text())
folder = Path(report['checkpoint']).parent
checkpoints = sorted(folder.glob('update-*.pt'), key=lambda p: int(p.stem.split('-')[-1]))
assert checkpoints, 'No saved checkpoint available; do not stop'
checkpoint = checkpoints[-1]

def processes():
    result = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            args = (entry/'cmdline').read_bytes().split(b'\0')
            args = [a.decode(errors='replace') for a in args if a]
            status = (entry/'status').read_text()
            parent = int(next(l.split()[1] for l in status.splitlines() if l.startswith('PPid:')))
            result[int(entry.name)] = (parent, args)
        except (OSError, StopIteration):
            pass
    return result

table = processes()
paths = {str(r/name) for name in ['run24-final-pipeline.py', 'run-recovered-head-adaptation.py', 'train-recovered-heads.py']}
roots = {pid for pid, (_, args) in table.items() if any(arg in paths for arg in args)}
trainers = {pid for pid in roots if str(r/'train-recovered-heads.py') in table[pid][1]}
assert len(trainers) <= 1
for pid in trainers:
    os.kill(pid, signal.SIGSTOP)
descendants = set(roots)
while True:
    new = {pid for pid, (parent, _) in table.items() if parent in descendants}
    if new <= descendants:
        break
    descendants |= new
for pid in roots-trainers:
    os.kill(pid, signal.SIGTERM)
for pid in trainers:
    os.kill(pid, signal.SIGINT)
    os.kill(pid, signal.SIGCONT)
time.sleep(3)
for pid in descendants:
    if Path(f'/proc/{pid}').exists():
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
time.sleep(2)
for pid in descendants:
    if Path(f'/proc/{pid}').exists():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

import torch
state = torch.load(checkpoint, map_location='cpu', weights_only=True)
assert 'optimizer_state_dict' in state and 'cuda_rng_states' in state
assert state['completed_updates'] == int(checkpoint.stem.split('-')[-1])
backup = r.parent/'models/challenge-paused'
backup.mkdir(parents=True, exist_ok=True)
destination = backup/'recovered-latest.pt'
shutil.copyfile(checkpoint, destination)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(checkpoint) == digest(destination)
shutil.copyfile(r/'recovered-adapted-v4.json', r/'recovered-adapted-v4-before-shutdown.json')
manifest = dict(status='paused_for_user_shutdown', stage='recovered_head_adaptation',
    checkpoint=str(checkpoint), backup_checkpoint=str(destination), sha256=digest(checkpoint),
    completed_updates=state['completed_updates'], target_updates=128,
    remaining_updates=128-state['completed_updates'], environment_steps=state['environment_steps'],
    workers=24, rollout=32, resume_available=True,
    note='Resume optimizer and CPU/CUDA RNG; recreate battles, not exact in-battle replay. Prior stages complete. Final holdout not yet run.',
    stopped_process_ids=sorted(descendants))
(r/'challenge-paused-state.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2), flush=True)
