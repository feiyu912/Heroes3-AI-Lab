"""Honor the user's new 24-worker setting while preserving the active checkpoint."""
import json
import os
from pathlib import Path
import signal
import time

r=Path('/mnt/g/Heroes3-AI-Lab/research')
marker=r/'training-switch-to24.json'
assert not marker.exists(),'One-time queue switch already performed'
targets={}
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:args=(p/'cmdline').read_bytes().split(b'\0')
    except FileNotFoundError:continue
    if len(args)>1 and args[1]==str(r/'run-challenge-training.py').encode():targets['supervisor']=int(p.name)
    if str(r/'train-ppo.py').encode() in args and str(r/'unlinked-v4-battleai.json').encode() in args:
        targets['trainer']=int(p.name)
assert set(targets)=={'supervisor','trainer'},targets
os.kill(targets['supervisor'],signal.SIGTERM)
os.kill(targets['trainer'],signal.SIGINT)
deadline=time.monotonic()+40
while Path('/proc/'+str(targets['trainer'])).exists():
    assert time.monotonic()<deadline,'Trainer did not finish checkpoint-preserving interruption'
    time.sleep(.25)
report=r/'unlinked-v4-battleai.json';log=r/'unlinked-v4-battleai.log'
report.rename(r/'unlinked-v4-partial-12.json');log.rename(r/'unlinked-v4-partial-12.log')
marker.write_text(json.dumps(dict(reason='User explicitly requested 24 parallel environments during the running comparison',
    pids=targets,checkpoint_preserved=True,original_partial_report=str(r/'unlinked-v4-partial-12.json'),
    note='Intentional interruption, not a completed experiment; continuation records actual budget and changed rollout horizon'),indent=2))
print('Preserved partial checkpoint; old 12-worker queue closed',flush=True)
