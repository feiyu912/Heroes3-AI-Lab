"""Explicit reviewed boundary continuation, no original source mutation or replay."""
import argparse,fcntl,hashlib,json,os,signal,sys,threading,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'battle-terminal-credit-native-20261023'
LAB=Path('/root/heroes3-ai-lab');SOURCE=LAB/'evaluations/battle-terminal-credit-01'
REVIEW=HERE.parent/'takeover-20261023/terminal-credit-recovery-review-01/AUDIT.json'
sys.path.insert(0,str(OLD))
import leases
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):
    p=Path(p);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(d,indent=2));os.replace(tmp,p)
def interrupt(signum,frame):raise KeyboardInterrupt('Recovery controller signal '+str(signum))
signal.signal(signal.SIGTERM,interrupt)
def telemetry(path,stop):
    with path.open('w') as out:
        while not stop.is_set():
            m={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
            out.write(json.dumps(dict(unix_time=time.time(),available_mib=m['MemAvailable']/1024,swap_used_mib=(m['SwapTotal']-m['SwapFree'])/1024))+'\n');out.flush()
            stop.wait(2)
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--evaluate',action='store_true');a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    reviewed=read(REVIEW);assert reviewed['recovery_boundary_verified'] and reviewed['original_run_passed'] is False
    original=read(SOURCE/'FREEZE.json');frozen=dict(original['input_sha256'])
    for path in (Path(__file__),HERE/'PLAN.md',REVIEW,SOURCE/'RESULT.json',SOURCE/'FREEZE.json',SOURCE/'control-phase-1/update-64.pt',SOURCE/'candidate-micro/update-62.pt'):frozen[str(path)]=sha(path)
    assert all(sha(k)==v for k,v in frozen.items())
    write(a.out/'FREEZE.json',dict(schema=original['schema'],input_sha256=frozen))
    plan=read(SOURCE/'PLAN.json');plan.update(execute=a.execute,evaluation=a.evaluate,recovery_review=str(REVIEW),original_run_failed=True,large_CPU_diagnostics_during_learning=False,original_learner_freeze=str(SOURCE/'FREEZE.json'))
    write(a.out/'PLAN.json',plan)
    if not a.execute:print(json.dumps(dict(plan_only=True,native_runs=0,optimizer_steps=0)));return 0
    result=dict(passed=False,original_run_passed=False,recovered_comparison=True,arms={},ability_promotion=False)
    env=dict(os.environ,LAB_PYTHON=str(LAB/'gpu-venv/bin/python'),LAB_STAGED_BOOT='1',LAB_WORKER_ROOT=str(LAB/'workers'/(a.out.name+'-bootstrap')),CUBLAS_WORKSPACE_CONFIG=':4096:8',TERMINAL_CREDIT_LEASE_OWNER='1')
    handles=[];stopped=threading.Event();monitor=None
    def invoke(arm,phase,checkpoint,expected):
        name=arm+'-phase-'+str(phase);out=a.out/name
        command=['bash','/mnt/g/Heroes3-AI-Lab/research/run-lab.sh',str(OLD/'train.py'),'--checkpoint',str(checkpoint),'--expected-sha',expected,'--freeze',str(SOURCE/'FREEZE.json'),'--out',str(out),'--arm',arm,'--phase-start',str(phase),'--phase-stop',str(phase+1)]
        with (a.out/(name+'.log')).open('w') as log:code=leases.run_owned(command,env=env,stream=log,pass_fds=[h.fileno() for h in handles])
        assert code==0,name+' gate failed; no retry'
        d=read(out/'RESULT.json');stop=phase+1
        assert d['passed'] and d['normal_workers_shutdown'] and d['actual_Adam_steps']==7680+256*stop
        assert d['admitted_stage_rows']==d['suffix_stage_rows']==1024*stop and d['total_native_stage_rows']==2048*stop
        assert [x['update'] for x in d['records']]==[61+phase*2,62+phase*2] and all(x['actual_Adam']==128 for x in d['records'])
        assert all(sha(k)==v for k,v in frozen.items())
        with (a.out/(name+'-audit.log')).open('w') as log:code=leases.run_owned([str(LAB/'venv/bin/python'),str(OLD/'audit.py'),'--stage',str(out)],env=env,stream=log,pass_fds=[h.fileno() for h in handles])
        assert code==0 and read(out/'AUDIT.json')['passed']
        result['arms'][arm]={k:d[k] for k in ('checkpoint','checkpoint_sha256','actual_Adam_steps','admitted_stage_rows','suffix_stage_rows','total_native_stage_rows')}
        result['arms'][arm]['new_Adam_steps']=d['actual_Adam_steps']-7680
        write(a.out/'RESULT.partial.json',result)
        return Path(d['checkpoint']),d['checkpoint_sha256']
    try:
        for path in leases.PATHS:
            h=path.open('a');fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(h)
        env['TERMINAL_CREDIT_LEASES']=json.dumps([leases.metadata(h,path) for h,path in zip(handles,leases.PATHS)])
        monitor=threading.Thread(target=telemetry,args=(a.out/'MEMORY.jsonl',stopped),daemon=True);monitor.start()
        control=SOURCE/'control-phase-1/update-64.pt';candidate=SOURCE/'candidate-micro/update-62.pt'
        assert sha(control)==reviewed['boundaries']['64']['sha256']
        result['arms']['control']=dict(checkpoint=str(control),checkpoint_sha256=sha(control),actual_Adam_steps=8192,new_Adam_steps=512,admitted_stage_rows=2048,suffix_stage_rows=2048,total_native_stage_rows=4096,recovered_post_resource_stop=True)
        ccp,csha=invoke('candidate',1,candidate,sha(candidate));bcp,bsha=control,sha(control)
        assert result['arms']['control']['actual_Adam_steps']==result['arms']['candidate']['actual_Adam_steps']==8192
        for phase in (2,3):
            bcp,bsha=invoke('control',phase,bcp,bsha)
            ccp,csha=invoke('candidate',phase,ccp,csha)
            assert result['arms']['control']['actual_Adam_steps']==result['arms']['candidate']['actual_Adam_steps']==7680+256*(phase+1)
        for h in reversed(handles):h.close()
        handles=[]
        if a.evaluate:
            with (a.out/'DEV-controller.log').open('w') as log:code=leases.run_owned([str(LAB/'venv/bin/python'),str(OLD/'evaluate.py'),'--run',str(a.out)],env=env,stream=log)
            assert code==0 and read(a.out/'DEV-RESULT.json')['passed'],'DEV invalid; no retry or checkpoint selection'
            result['DEV']=read(a.out/'DEV-RESULT.json')['DEV']
        result['passed']=True
    except BaseException as error:result['error']=repr(error)
    finally:
        leases.finish_owned_groups();stopped.set()
        if monitor:monitor.join(timeout=4)
        for h in reversed(handles):h.close()
        write(a.out/'RESULT.json',result)
    print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
