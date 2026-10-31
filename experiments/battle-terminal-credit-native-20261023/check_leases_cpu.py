"""Real flock/pass_fds/process-group regression on isolated temporary files only."""
import argparse,fcntl,json,os,subprocess,sys,tempfile,time
from pathlib import Path
import leases
def free(path):
    with path.open('a') as h:
        try:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return False
        return True
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);package=Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='terminal-credit-lease-cpu-') as tmp:
        root=Path(tmp);paths=[root/name for name in ['.gpu-learner-lock','.pool-lock']];handles=[x.open('a') for x in paths]
        for h in handles:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        entries=[leases.metadata(h,x) for h,x in zip(handles,paths)];assert leases.verify(entries,paths)['passed']
        wrong=[dict(x) for x in entries];wrong[0]['inode']+=1
        try:leases.verify(wrong,paths)
        except AssertionError:pass
        else:raise AssertionError('Wrong inode accepted')
        ready=root/'ready.json';script="import json,os,pathlib,subprocess,sys,time;import leases;v=leases.verify(json.loads(os.environ['CPU_ENTRIES']),[pathlib.Path(x) for x in json.loads(os.environ['CPU_PATHS'])]);child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);pathlib.Path(os.environ['CPU_READY']).write_text(json.dumps(dict(proof=v,descendant=child.pid)));time.sleep(60)"
        env=dict(os.environ,PYTHONPATH=str(package),CPU_ENTRIES=json.dumps(entries),CPU_PATHS=json.dumps(list(map(str,paths))),CPU_READY=str(ready))
        child=subprocess.Popen([sys.executable,'-c',script],env=env,start_new_session=True,pass_fds=tuple(h.fileno() for h in handles))
        deadline=time.monotonic()+5
        while not ready.exists() and time.monotonic()<deadline:time.sleep(.05)
        assert ready.exists();proof=json.loads(ready.read_text());assert proof['proof']['passed']
        for h in handles:h.close()
        assert not any(free(path) for path in paths),'Child lost inherited actual leases when controller copies closed'
        leases.stop_group(child);assert not leases.live_group_members(child.pid) and all(free(path) for path in paths)
        # ENV/metadata without a real held flock must fail, never acquire it.
        handles=[x.open('a') for x in paths];entries=[leases.metadata(h,x) for h,x in zip(handles,paths)]
        try:leases.verify(entries,paths)
        except AssertionError as error:assert 'not already exclusively held' in str(error)
        else:raise AssertionError('Unheld file accepted as a lease')
        for h in handles:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
        exit_script="import subprocess,sys;subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);raise SystemExit(7)"
        with (root/'failure.log').open('w') as log:code=leases.run_owned([sys.executable,'-c',exit_script],env=env,stream=log,pass_fds=tuple(h.fileno() for h in handles))
        assert code==7 and not leases.ACTIVE_GROUPS
        for h in handles:h.close()
        assert all(free(path) for path in paths)
    result=dict(passed=True,inherited_kernel_flocks_survive_controller_fd_close=True,wrong_inode_rejected=True,unheld_metadata_ENV_rejected=True,independent_session_descendants_stopped_before_release=True,failed_child_live_descendants_cleaned=True,temporary_test_locks_only=True,shared_resource_locks_taken=False,new_native_games=0,GPU_operations=0,optimizer_steps=0)
    (a.out/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
