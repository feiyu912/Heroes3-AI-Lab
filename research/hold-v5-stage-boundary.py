"""Let the current head run finish, then switch to reviewed next-stage control."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time
from lab_io import atomic_json

r=Path('/mnt/g/Heroes3-AI-Lab/research')
supervisors=[]
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:args=(p/'cmdline').read_bytes().split(b'\0')
    except OSError:continue
    if str(r/'run-goal-v5.py').encode() in args:supervisors.append(int(p.name))
assert len(supervisors)==1
supervisor=supervisors[0];replaced=False
os.kill(supervisor,signal.SIGSTOP)
atomic_json(r/'v5-boundary-hold.json',dict(state='holding_supervisor_only',pid=supervisor,
    reason='Current training completes normally; validate central GPU batching and align selection with actual goal before next stages'))
try:
    deadline=time.monotonic()+1800
    while time.monotonic()<deadline:
        report=json.loads((r/'v5-diverse-heads.json').read_text())
        marker=r/'v5-boundary-ready.json'
        if report.get('completed') and report.get('all_workers_exit_zero') and marker.exists():break
        time.sleep(5)
    else:raise TimeoutError('Stage boundary handoff timed out; old supervisor will resume')
    assert json.loads((r/'v5-boundary-ready.json').read_text())['ready']
    with (r/'central-opponent-benchmark.log').open('wb') as log:
        result=subprocess.run(['python3',str(r/'benchmark-central-opponent.py')],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    assert result.returncode==0,'Central batching benchmark failed; old supervisor will resume'
    os.kill(supervisor,signal.SIGTERM);os.kill(supervisor,signal.SIGCONT)
    time.sleep(1)
    with (r/'goal-v5-replacement.log').open('wb') as log:
        process=subprocess.Popen(['python3',str(r/'run-goal-v5.py')],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    replaced=True
    atomic_json(r/'v5-boundary-hold.json',dict(state='replaced_at_completed_training_boundary',old_pid=supervisor,new_pid=process.pid,
        head_training_completed=True,weights_and_optimizer_preserved=True))
    print('Next-stage supervisor running',process.pid,flush=True)
finally:
    if not replaced:
        try:os.kill(supervisor,signal.SIGCONT)
        except ProcessLookupError:pass
