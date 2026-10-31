"""Record stopped state and preserve last completed models after user pause."""
import fcntl
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

lab = Path('/root/heroes3-ai-lab')
run = lab / 'evaluations/battle-continuation-lr-paired-01'
out = Path(__file__).resolve().parent / 'user-pause-01'
out.mkdir(exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
processes = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        argv = (proc / 'cmdline').read_bytes().decode().strip('\0').split('\0')
        maps = (proc / 'maps').read_text(errors='replace')
        native = '/root/heroes3-ai-lab/' in maps and '/libvcmi.so' in maps
        learner = any(arg.endswith('/train_last_graph.py') for arg in argv) and any(str(run) in arg for arg in argv)
        controller = any(arg.endswith('/run.py') for arg in argv) and str(run) in argv
        if native or learner or controller:
            processes.append(dict(pid=int(proc.name), argv=argv, native_library=native))
    except (FileNotFoundError, PermissionError, ProcessLookupError):
        continue
gpu = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid,process_name', '--format=csv,noheader'], text=True).strip()
locks = []
handles = []
try:
    for name in ('.gpu-learner-lock', '.pool-lock'):
        h = (lab / 'evaluations' / name).open('a')
        handles.append(h)
        fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locks.append(name)
finally:
    for h in reversed(handles):
        h.close()
assert not processes, processes
assert not gpu, gpu
saved = {}
for arm in ('control', 'candidate'):
    report_path = run / arm / 'training.json'
    report = json.loads(report_path.read_text())
    record = report['records'][-1]
    source = Path(report['checkpoint'])
    assert sha(source) == record['checkpoint_sha256']
    target = out / (arm + '-' + source.name)
    shutil.copyfile(source, target)
    assert sha(target) == sha(source)
    saved[arm] = dict(global_update=record['update'], stage_updates=len(report['records']),
        new_Adam_steps=record['actual_Adam_steps_this_stage'], cumulative_Adam_steps=record['actual_Adam_steps_total'],
        checkpoint=str(source), copy=str(target), sha256=sha(source),
        native_environment_restorable=False)
    shutil.copyfile(report_path, out / (arm + '-training.json'))
shutil.copyfile(run / 'RESULT.json', out / 'controller-RESULT.json')
result = dict(user_requested_pause=True, stopped=True, active_native_or_learner_processes=processes,
    GPU_compute_apps=gpu, locks_verified_available=locks, saved=saved,
    final_DEV_games_run=0, ability_improvement_claim=False,
    note='KeyboardInterrupt is a user pause, not a game defeat. In-flight sample is not a completed update; last complete checkpoints retained. Resume requires an explicit remaining schedule, not blindly replaying this fixed-parent controller.')
(out / 'PAUSE.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
