"""Check lab processes without passing regex alternation through Windows/WSL shells."""
import json
from pathlib import Path

names={'run24-final-pipeline.py','run-recovered-head-adaptation.py','train-recovered-heads.py',
       'resume-paused-challenge.py','evaluate-battles.py'}
active=[]
workers=[]
for directory in Path('/proc').iterdir():
    if not directory.name.isdigit():continue
    try:args=[x.decode(errors='replace') for x in (directory/'cmdline').read_bytes().split(b'\0') if x]
    except OSError:continue
    if any(a.startswith('/mnt/g/Heroes3-AI-Lab/research/') and Path(a).name in names for a in args):
        active.append(dict(pid=int(directory.name),args=args))
    if args and args[0].startswith('/root/heroes3-ai-lab/') and '--multiprocessing-fork' in args:
        workers.append(int(directory.name))
print(json.dumps(dict(active_lab_processes=active,active_lab_workers=workers),indent=2))
assert not active and not workers,'Lab work is still running'
