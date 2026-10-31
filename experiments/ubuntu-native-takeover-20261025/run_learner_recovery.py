"""Controller for a zero-update learner recovery in the explicit Ubuntu profile."""
import fcntl,hashlib,json,os,signal,subprocess
from pathlib import Path
import leases
HERE=Path(__file__).resolve().parent
PROFILE=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Native-20261025')
OUT=HERE/'learner-recovery-actual-01'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def interrupt(signum,frame):raise KeyboardInterrupt('Recovery interrupted')
def main():
    assert json.loads((PROFILE/'AUDIT.json').read_text())['passed']
    assert json.loads((HERE/'battle-runtime-02/RESULT.json').read_text())['passed']
    assert json.loads((HERE/'gradient-support/actual-02/AUDIT.json').read_text())['passed']
    assert not OUT.exists()
    command=[str(PROFILE/'runtime/python-heroes3.sh'),str(HERE/'learner-recovery-v2/qualify.py'),
      '--checkpoint',str(HERE/'restored-history/root/heroes3-ai-lab/evaluations/battle-observed-MC-probe-01/MC-update-62.pt'),
      '--prefix',str(HERE/'verified-repair/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01/candidate-micro/phase-0/admitted-1.pt'),
      '--profile-certificate',str(HERE/'python-integrity/PROFILE_CERTIFICATE.json'),'--out',str(OUT)]
    fs=[]
    try:
        leases.LAB.mkdir(parents=True,exist_ok=True)
        for path in leases.PATHS:
            f=path.open('a+');fs.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        entries=[leases.metadata(f,p) for f,p in zip(fs,leases.PATHS)]
        env=dict(os.environ,TERMINAL_CREDIT_LEASES=json.dumps(entries),TERMINAL_CREDIT_POOL_LEASE=json.dumps(entries[1]),LAB_WORKER_ROOT=str(PROFILE/'runtime/workers/learner-recovery-actual-01'))
        assert env.get('CUDA_VISIBLE_DEVICES') not in ('','-1'),'CUDA is hidden in controller environment'
        with (HERE/'LEARNER_RECOVERY.log').open('xb') as stream:
            child=subprocess.Popen(command,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=tuple(f.fileno() for f in fs))
            try:
                code=child.wait(timeout=300)
                assert not leases.live_group_members(child.pid),'Recovery descendants survived'
            finally:
                if child.poll() is None or leases.live_group_members(child.pid):leases.stop_group(child)
        assert code==0
        result=json.loads((OUT/'RESULT.json').read_text());assert result['passed'] and result['optimizer_step_calls']==0 and result['actual_Adam_steps']==7936
        (HERE/'LEARNER_RECOVERY_CONTROLLER.json').write_text(json.dumps(dict(passed=True,command=command,worker_exit=code,optimizer_step_calls=0,leases=entries,owned_group_drained=True,result_sha256=sha(OUT/'RESULT.json'),controller_sha256=sha(__file__)),indent=2))
    finally:
        for f in reversed(fs):f.close()
if __name__=='__main__':
    signal.signal(signal.SIGINT,interrupt);signal.signal(signal.SIGTERM,interrupt);main()
