"""Pause only the identified experiment learner; preserve completed checkpoints."""
import argparse
import json
import os
import signal
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--stop', action='store_true')
a = p.parse_args()
root = '/root/heroes3-ai-lab/evaluations/battle-continuation-lr-paired-01'
found = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit() or int(proc.name) == os.getpid():
        continue
    try:
        argv = (proc / 'cmdline').read_bytes().decode().strip('\0').split('\0')
        if not any(arg.startswith(root) for arg in argv):
            continue
        if not any(arg.endswith('/train_last_graph.py') or arg.endswith('/run.py') for arg in argv):
            continue
        found.append(dict(pid=int(proc.name), argv=argv,
                          learner=any(arg.endswith('/train_last_graph.py') for arg in argv)))
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        continue
print(json.dumps({'identified': found}, indent=2), flush=True)
if a.stop:
    learners = [r for r in found if r['learner']]
    assert len(learners) <= 1, 'Do not signal an ambiguous set'
    for learner in learners:
        # Python handles KeyboardInterrupt via its existing evidence/abort path.
        os.kill(learner['pid'], signal.SIGINT)
        print(json.dumps({'SIGINT_sent_to_exact_learner': learner['pid']}), flush=True)
