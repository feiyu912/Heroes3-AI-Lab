"""Private synthetic termination, held-lock exclusion and identity-rejection tests."""
import fcntl
import json
from pathlib import Path
import subprocess
import sys
import time

from measure import batch_processes

here = Path(__file__).resolve().parent
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=False)
case = out / 'interrupt-case'
with (out/'supervisor.log').open('w') as log:
    proc = subprocess.Popen([sys.executable, str(here/'measure.py'), '--out', str(case), '--execute', '--synthetic', '--stages', '1,2', '--repeats', '3'], stdout=log, stderr=subprocess.STDOUT)
    deadline = time.monotonic()+10
    ready = case/'supervisor-ready.json'
    while (not ready.exists() or not list(case.glob('scale-*/job-*/native-pid.json'))) and time.monotonic()<deadline:
        time.sleep(.02)
    if not ready.exists():
        proc.kill()
        raise RuntimeError('Synthetic supervisor did not become ready')
    info = json.loads(ready.read_text())
    plan = json.loads((case/'protocol.json').read_text())
    lockpath = Path(info['lock'])
    with lockpath.open('a') as competitor:
        blocked_during = False
        try:
            fcntl.flock(competitor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            blocked_during = True
    proc.terminate()
    exitcode = proc.wait(timeout=15)
    with lockpath.open('a') as competitor:
        fcntl.flock(competitor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        free_after = True
    remaining = batch_processes(info['token'])
    result = json.loads((case/'result.json').read_text())
    report = dict(synthetic_only=True, no_real_pool_or_game_or_gpu=True, blocked_during=blocked_during,
                  free_after=free_after, remaining_processes=remaining, supervisor_exit=exitcode,
                  result_status=result['status'])
    # Wrong inode must fail before creating a native process, even with real FD.
    rejection = out/'inode-rejection'
    rejection.mkdir()
    with lockpath.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        identity = lockpath.stat()
        command = [sys.executable, str(here/'worker_runner.py'), '--map', 'Maps/adv/takeover-v2-train-01-mines',
                   '--pool-lock-fd', str(lock.fileno()), '--pool-lock-dev', str(identity.st_dev), '--pool-lock-inode', str(identity.st_ino+1),
                   '--report-dir', str(rejection), '--native-pid-file', str(rejection/'native-pid.json'), '--lab-root', plan['lab']]
        check = subprocess.run(command, pass_fds=(lock.fileno(),), capture_output=True, text=True, timeout=10)
    (rejection/'worker.log').write_text(check.stdout+check.stderr)
    report['wrong_inode_rejected'] = check.returncode != 0 and 'inode/device mismatch' in check.stderr and not (rejection/'native-pid.json').exists()
    unlocked = out/'unlocked-fd-rejection'
    unlocked.mkdir()
    with lockpath.open('a') as lock:
        command = [sys.executable, str(here/'worker_runner.py'), '--map', 'Maps/adv/takeover-v2-train-01-mines',
                   '--pool-lock-fd', str(lock.fileno()), '--pool-lock-dev', str(identity.st_dev), '--pool-lock-inode', str(identity.st_ino),
                   '--report-dir', str(unlocked), '--native-pid-file', str(unlocked/'native-pid.json'), '--lab-root', plan['lab']]
        check = subprocess.run(command, pass_fds=(lock.fileno(),), capture_output=True, text=True, timeout=10)
    (unlocked/'worker.log').write_text(check.stdout+check.stderr)
    report['unlocked_fd_rejected'] = check.returncode != 0 and 'lock was not exclusive' in check.stderr and not (unlocked/'native-pid.json').exists()
    report['passed'] = blocked_during and free_after and not remaining and exitcode != 0 and report['wrong_inode_rejected'] and report['unlocked_fd_rejected']
    (out/'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
