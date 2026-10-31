"""Validate inherited canonical leases immediately before exec of build command."""
import errno, fcntl, json, os, sys
from pathlib import Path

entries = json.loads(os.environ['HEROES3_BUILD_LEASES'])
assert [Path(e['path']).name for e in entries] == ['.gpu-learner-lock', '.pool-lock']
for entry in entries:
    inherited = os.fstat(entry['fd'])
    current = Path(entry['path']).stat()
    assert (inherited.st_dev, inherited.st_ino) == (current.st_dev, current.st_ino) == (entry['device'], entry['inode'])
    with Path(entry['path']).open('r+') as probe:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            assert error.errno in (errno.EACCES, errno.EAGAIN)
        else:
            fcntl.flock(probe, fcntl.LOCK_UN)
            raise AssertionError('Independent lock unexpectedly acquired')
    fcntl.flock(entry['fd'], fcntl.LOCK_EX | fcntl.LOCK_NB)
proof = dict(passed=True, PID=os.getpid(), entries=entries, independent_open_conflict=True)
(Path(os.environ['HEROES3_BUILD_STAGE']) / 'CHILD_LEASES.json').write_text(json.dumps(proof, indent=2) + '\n')
os.execvpe(sys.argv[1], sys.argv[1:], os.environ)
