"""Read-only check for recovery lease availability and residual native processes."""
import fcntl
import json
import os
from pathlib import Path

LAB = Path('/root/heroes3-ai-lab/evaluations')
locks = {}
for name in ['.gpu-learner-lock', '.pool-lock']:
    path = LAB / name
    handle = path.open('a')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks[str(path)] = 'free'
        fcntl.flock(handle, fcntl.LOCK_UN)
    except BlockingIOError:
        locks[str(path)] = 'busy'
    finally:
        handle.close()
needles = ['train.py', 'learner_impl', 'vcmi', 'VCMI', 'recorded_vector',
           'evaluate_policy_steps', 'recovery_02.py', 'boundary_audit_02.py']
found = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        cmd = (proc / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace')
    except OSError:
        continue
    if any(needle in cmd for needle in needles):
        found.append(dict(pid=int(proc.name), cmd=cmd))
print(json.dumps(dict(locks=locks, processes=found), indent=2))
assert all(value == 'free' for value in locks.values())
assert not found
