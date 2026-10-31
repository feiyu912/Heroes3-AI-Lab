"""Clean up only the optional native CUDA probe and its children."""
import os
from pathlib import Path
import signal
import time

table={}
for path in Path('/proc').iterdir():
    if not path.name.isdigit():continue
    try:
        args=[x.decode(errors='replace') for x in (path/'cmdline').read_bytes().split(b'\0') if x]
        parent=int(next(l.split()[1] for l in (path/'status').read_text().splitlines() if l.startswith('PPid:')))
        table[int(path.name)]=(parent,args)
    except (OSError,StopIteration):pass
targets={pid for pid,(_,args) in table.items() if '/mnt/g/Heroes3-AI-Lab/research/test-native-cuda.py' in args}
while True:
    children={pid for pid,(parent,_) in table.items() if parent in targets}
    if children<=targets:break
    targets|=children
for pid in targets:
    try:os.kill(pid,signal.SIGTERM)
    except ProcessLookupError:pass
time.sleep(1)
for pid in targets:
    try:os.kill(pid,signal.SIGKILL)
    except ProcessLookupError:pass
print('Stopped only optional native CUDA probe processes',sorted(targets))
