"""Inherited real flock descriptors, inode validation and owned-session cleanup."""
import errno,fcntl,json,os,signal,subprocess,time
from pathlib import Path
LAB=Path('/root/heroes3-ai-lab/evaluations')
PATHS=[LAB/'.gpu-learner-lock',LAB/'.pool-lock']
ACTIVE_GROUPS=set()
def metadata(handle,path):
    st=os.fstat(handle.fileno());return dict(fd=handle.fileno(),path=str(path),device=st.st_dev,inode=st.st_ino)
def verify(entries,paths):
    assert len(entries)==len(paths) and len({x['fd'] for x in entries})==len(entries)
    for entry,path in zip(entries,paths):
        assert entry['path']==str(path);fd=int(entry['fd']);saved=os.fstat(fd);current=Path(path).stat()
        assert (saved.st_dev,saved.st_ino)==(current.st_dev,current.st_ino)==(entry['device'],entry['inode']),'Inherited lease inode differs'
        # A separate open description must fail before we touch the inherited
        # description, so a missing lock cannot be silently acquired here.
        with Path(path).open('a') as probe:
            try:fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError as error:assert error.errno in (errno.EACCES,errno.EAGAIN)
            else:
                fcntl.flock(probe,fcntl.LOCK_UN);raise AssertionError('Lease was not already exclusively held')
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)  # Must be OUR inherited description.
    return dict(passed=True,PID=os.getpid(),entries=entries,inherited_flock_verified=True)
def verify_pair():
    entries=json.loads(os.environ['TERMINAL_CREDIT_LEASES']);return verify(entries,PATHS)
def verify_pool():
    return verify([json.loads(os.environ['TERMINAL_CREDIT_POOL_LEASE'])],[PATHS[1]])
def live_group_members(pgid):
    found=[]
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            fields=path.read_text().rsplit(')',1)[1].split()
            if int(fields[2])==pgid and fields[0] not in ('Z','X'):found.append(int(path.parent.name))
        except (FileNotFoundError,ProcessLookupError,ValueError,IndexError):pass
    return found
def stop_group(process,grace=5.):
    pgid=process.pid
    try:os.killpg(pgid,signal.SIGTERM)
    except ProcessLookupError:pass
    deadline=time.monotonic()+grace
    while live_group_members(pgid) and time.monotonic()<deadline:time.sleep(.05)
    if live_group_members(pgid):
        try:os.killpg(pgid,signal.SIGKILL)
        except ProcessLookupError:pass
    process.wait(timeout=5)
    deadline=time.monotonic()+3
    while live_group_members(pgid) and time.monotonic()<deadline:time.sleep(.05)
    assert not live_group_members(pgid),'Live learner/worker process group remains; do not release leases'
def run_owned(command,*,env,stream,pass_fds=()):
    process=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=tuple(pass_fds))
    ACTIVE_GROUPS.add(process.pid)
    try:
        code=process.wait()
        if code!=0:stop_group(process)
        else:
            deadline=time.monotonic()+2
            while live_group_members(process.pid) and time.monotonic()<deadline:time.sleep(.05)
            assert not live_group_members(process.pid),'Child exited while worker group still alive'
        ACTIVE_GROUPS.discard(process.pid)
        return code
    except BaseException:
        stop_group(process);ACTIVE_GROUPS.discard(process.pid);raise
def finish_owned_groups():
    # If an uninterruptible descendant survives the first kill attempt, keep
    # this controller alive holding its leases until no owned live task remains.
    while any(live_group_members(pgid) for pgid in ACTIVE_GROUPS):
        for pgid in list(ACTIVE_GROUPS):
            try:os.killpg(pgid,signal.SIGKILL)
            except ProcessLookupError:pass
        try:time.sleep(.1)
        except KeyboardInterrupt:continue
    ACTIVE_GROUPS.clear()
