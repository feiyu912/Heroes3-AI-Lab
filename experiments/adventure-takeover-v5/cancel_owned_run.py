#!/usr/bin/env python3
"""Stop only a runner-owned session after verifying its exact working directory."""
import argparse
import json
import os
from pathlib import Path
import signal

p = argparse.ArgumentParser()
p.add_argument('run_dir', type=Path)
p.add_argument('--reason', required=True)
a = p.parse_args()
run = a.run_dir.resolve(strict=True)
root = Path('/root/heroes3-ai-lab/workers/adv-runs').resolve()
if run.parent != root or not (run / 'plan.json').exists():
    raise SystemExit('Unrecognized run directory')
stopped = []
for entry in Path('/proc').iterdir():
    if not entry.name.isdigit():
        continue
    try:
        if (entry / 'comm').read_text().strip() != 'vcmiclient' or (entry / 'cwd').resolve() != run:
            continue
        pid = int(entry.name)
        if os.getpgid(pid) != pid:
            raise RuntimeError('Expected an isolated runner process group')
        os.killpg(pid, signal.SIGTERM)
        stopped.append(pid)
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        continue
record = dict(cancelled=True, reason=a.reason, verified_run_dir=str(run), stopped_groups=stopped)
(run / 'CANCELLED.json').write_text(json.dumps(record, indent=2))
print(json.dumps(record))
