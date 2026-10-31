"""Synthetic session-cleanup check: no game, GPU or shared simulation lock."""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

runner_path = Path(__file__).resolve().parents[1] / 'adventure_runner_v5.py'
if len(sys.argv) > 1 and sys.argv[1] == '--stub-runner':
    root = Path(sys.argv[2])
    spec = importlib.util.spec_from_file_location('runner', runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.LAB = root
    runner.BIN = root / 'bin'
    runner.SHARED = root / 'shared'
    sys.argv = [str(runner_path), '--map', 'Maps/adv/stub', '--seconds', '30']
    raise SystemExit(runner.main())

out = Path(sys.argv[1])
if out.exists():
    raise ValueError('Refuse overwrite')
root = Path(tempfile.mkdtemp(prefix='synthetic-runner-cleanup-'))
for name in ('bin/config', 'data/vcmi/Maps/adv', 'data/vcmi/Data', 'data/vcmi/Mods', 'evaluations'):
    (root / name).mkdir(parents=True)
(root / 'data/vcmi/Maps/adv/stub.vmap').write_text('synthetic; not a native map')
for name in ('vcmiserver', 'libvcmi.so'):
    (root / 'bin' / name).write_text('synthetic')
engine = root / 'bin/vcmiclient'
engine.write_text('#!' + sys.executable + '''
import os, signal, time
from pathlib import Path
pid = os.fork()
if pid == 0:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    Path('stubborn-child.pid').write_text(str(os.getpid()))
    while True: time.sleep(1)
while True: time.sleep(1)
''')
engine.chmod(0o755)
with (root / 'wrapper.log').open('w') as log:
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--stub-runner', str(root)], stdout=log, stderr=subprocess.STDOUT)
    deadline = time.monotonic() + 10
    pidfiles = []
    while not pidfiles and time.monotonic() < deadline:
        pidfiles = list(root.glob('workers/adv-runs/*/stubborn-child.pid'))
        time.sleep(.02)
    if not pidfiles:
        proc.kill()
        raise RuntimeError('Synthetic engine did not start')
    child = int(pidfiles[0].read_text())
    held_before = False
    with (root / 'evaluations/.pool-lock').open('r+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            held_before = True
    proc.terminate()
    code = proc.wait(timeout=12)
    time.sleep(.05)
    stat_path = Path(f'/proc/{child}/stat')
    child_state = stat_path.read_text().split()[2] if stat_path.exists() else 'gone'
    with (root / 'evaluations/.pool-lock').open('r+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        free_after = True
    result = json.loads(next(root.glob('workers/adv-runs/*/result.json')).read_text())
    report = dict(synthetic_only=True, no_game_executed=True, temporary_root=str(root),
                  child_state_after=child_state, held_before=held_before, free_after=free_after,
                  wrapper_exit=code, native_result=result)
    report['passed'] = held_before and free_after and child_state in ('gone', 'Z') and result['interrupted'] and not result['completed']
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
