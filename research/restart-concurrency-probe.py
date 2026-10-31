"""Replace the waiting probe supervisor; active training is untouched."""
import os
from pathlib import Path
import signal
import subprocess

script='/mnt/g/Heroes3-AI-Lab/research/measure-challenge-concurrency.py'
pids=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit(): continue
    try:
        args=(p/'cmdline').read_bytes().split(b'\0')
        if len(args)>1 and args[1]==script.encode():pids.append(int(p.name))
    except FileNotFoundError:pass
assert len(pids)==1,pids
os.kill(pids[0],signal.SIGTERM)
print('Replaced waiting benchmark with staged 12–48 configuration probe',flush=True)
subprocess.run(['python3',script],check=True)
