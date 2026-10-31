"""Read-only runtime snapshot; nonblocking lock probes are immediately released."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

LAB = Path('/root/heroes3-ai-lab')
SHARED = Path('/mnt/g/Heroes3-AI-Lab')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


out = Path(sys.argv[1])
if out.exists():
    raise ValueError('Refuse overwrite of earlier snapshot')
report = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), locks={}, processes=[])
for name in ('.pool-lock', '.gpu-learner-lock'):
    path = LAB / 'evaluations' / name
    with path.open('r+') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            report['locks'][str(path)] = 'free_at_probe'
            fcntl.flock(stream, fcntl.LOCK_UN)
        except BlockingIOError:
            report['locks'][str(path)] = 'held_at_probe'
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        cmd = path.read_bytes().replace(b'\0', b' ').decode(errors='replace')
        if int(path.parent.name) != os.getpid() and any(s in cmd for s in ('vcmiclient', 'vcmiserver', 'train_ppo', 'broker.py', 'replay_rollout.py')):
            report['processes'].append(dict(pid=int(path.parent.name), cmdline=cmd))
    except (OSError, ValueError):
        pass
paths = [SHARED / 'experiments/strategic-policy-v1/ppo-pilot-02' / n for n in ('training.json', 'update-1.pt', 'update-2.pt')]
paths += [LAB / 'models/graph-finetune/1792068859379237126/update-64.pt']
paths += [LAB / 'src/gym/vcmi/rel/bin' / n for n in ('libvcmi.so', 'libmlserverplugin.so', 'vcmiserver', 'vcmiclient', 'libmlclient.so')]
report['sha256'] = {str(p): sha(p) for p in paths}
report['frozen_verify'] = subprocess.run(['bash', str(SHARED / 'experiments/adv-verify-frozen.sh')], capture_output=True, text=True).__dict__
report['gpu'] = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu', '--format=csv'], capture_output=True, text=True).__dict__
out.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
