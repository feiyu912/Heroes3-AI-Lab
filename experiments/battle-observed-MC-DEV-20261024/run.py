"""Fixed96 CPU-native DEV, strict historical gates and full NN replay."""
import argparse,concurrent.futures,contextlib,fcntl,json,os,signal,subprocess,sys,threading,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;R=ROOT/'research';LAB=Path('/root/heroes3-ai-lab')
sys.path[:0]=[str(HERE),str(R),str(LAB/'src/gym')]
import leases
import dev_utils as helper
import dev_raw_auditor as independent
SOURCE=LAB/'evaluations/battle-observed-MC-probe-01';HISTORY=LAB/'evaluations/battle-terminal-credit-01/candidate-micro'
ACTIVE=set();MUTEX=threading.Lock()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def stop(signum,frame):
    with MUTEX:
        for pg in ACTIVE:
            try:os.killpg(pg,signal.SIGTERM)
            except ProcessLookupError:pass
    raise KeyboardInterrupt('DEV interrupted; owned sessions stopped')
signal.signal(signal.SIGTERM,stop)
def resources(root,phase,initial=False):
    m={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    q=dict(phase=phase,available_mib=m['MemAvailable']/1024,swap_mib=(m['SwapTotal']-m['SwapFree'])/1024)
    with (root/'RESOURCES.jsonl').open('a') as f:f.write(json.dumps(q)+'\n')
    assert q['available_mib']>(4096 if initial else 2048) and q['swap_mib']<256
@contextlib.contextmanager
def owned():
    fs=[]
    try:
        for path in leases.PATHS:
            f=path.open('a+');fs.append(f);fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield fs
    finally:
        for f in reversed(fs):f.close()
def child(argv,env,log,fds):
    with log.open('wb') as stream:
        p=subprocess.Popen(argv,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,pass_fds=fds)
        with MUTEX:ACTIVE.add(p.pid)
        try:
            try:code=p.wait(timeout=300)
            except subprocess.TimeoutExpired:leases.stop_group(p);raise
            if leases.live_group_members(p.pid):leases.stop_group(p);raise AssertionError('Worker group survived exit')
            return code
        finally:
            if p.poll() is None or leases.live_group_members(p.pid):leases.stop_group(p)
            with MUTEX:ACTIVE.discard(p.pid)
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args();root=a.out
    producer=helper.read(SOURCE/'RESULT.json');assert producer['passed'] and producer['reference_reproduction_exact'] and producer['four_RNG_draw_recovery_exact']
    models=[('parent60',LAB/'evaluations/battle-continuation-lr-paired-01/control/models/1792508024116623978/update-60.pt'),('control',HISTORY/'update-62.pt'),('candidate',Path(producer['checkpoint']))]
    assert helper.sha(models[0][1])=='443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20'
    assert helper.sha(models[1][1])=='ec26fe4bcd0987a01821f2076a4d076589008a88f6a41a63d00d5c9c0cfd0eec'
    assert helper.sha(models[2][1])=='5cd856b3221342c283899df126f4c50116d7779b3e0ea3b8d90125e243310354'
    frozen=helper.read(HERE/'SOURCE_FREEZE.json')['input_sha256'];assert all(helper.sha(p)==h for p,h in frozen.items())
    root.mkdir(parents=True,exist_ok=False);plan=dict(parent_checkpoint=str(models[0][1]),models={k:dict(path=str(v),sha256=helper.sha(v)) for k,v in models},seed_base=2026109400,scenarios=list(range(192,200)),execute=a.execute,optimizer_steps=0,final_test_touched=False)
    write(root/'PLAN.json',plan);write(root/'FREEZE.json',dict(input_sha256=frozen));reports=[]
    partial=dict(arms={k:dict(checkpoint=str(v),checkpoint_sha256=helper.sha(v)) for k,v in models if k!='parent60'},DEV=reports)
    if not a.execute:return 0
    result=dict(passed=False,optimizer_steps=0,model_promoted=False,final_test_touched=False)
    try:
        resources(root,'start',True)
        with owned() as fs:
            for model,checkpoint in models:
                for opponent in ('BattleAI','MMAI_MODEL'):
                    resources(root,model+'/'+opponent+'/before');assert all(helper.sha(p)==h for p,h in frozen.items())
                    run_id=str(time.time_ns());folder=LAB/'evaluations'/run_id;folder.mkdir()
                    def one(job):
                        idx,role=job;seed=2026109400+idx*100;name=f'{idx}-{role}-{seed}-recovered';output=folder/(name+'.json');log=folder/(name+'.log')
                        env=dict(os.environ,LAB_PYTHON=str(LAB/'venv/bin/python'),LAB_STAGED_BOOT='1',LAB_WORKER_ROOT=str(LAB/'workers'/('eval-'+run_id)/name),TERMINAL_CREDIT_POOL_LEASE=json.dumps(leases.metadata(fs[1],leases.PATHS[1])))
                        argv=['bash',str(R/'run-lab.sh'),str(HERE/'evaluate_policy_steps.py'),'--scenario',str(idx),'--role',role,'--seed',str(seed),'--policy','recovered','--checkpoint',str(checkpoint),'--output',str(output),'--scenarios',str(R/'diverse-curriculum.json'),'--opponent',opponent,'--teacher-turns','2']
                        if opponent=='MMAI_MODEL':argv+=['--opponent-model','DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx']
                        code=child(argv,env,log,tuple(f.fileno() for f in fs));return helper.finalize(output,log,code)
                    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:games=list(pool.map(one,[(i,r) for i in range(192,200) for r in ('attacker','defender')]))
                    wins=sum(g['success'] for g in games);loss=sum(sum(g['terminal_outcome']['casualties'][str(int(g['role']=='defender'))].values()) for g in games)
                    summary=dict(policy='recovered',battles=16,wins=wins,win_rate=wins/16,mean_permanent_units_lost=loss/16,truncated=0,non_normal_terminations=0,invalid_actions=0)
                    report=root/(model+'-'+opponent+'.json');write(report,dict(run_id=run_id,checkpoint=str(checkpoint),opponent=opponent,scenario_file=str(R/'diverse-curriculum.json'),scenario_ids=list(range(192,200)),battles=games,summary=[summary],frozen_artifacts=frozen,artifacts_checked_before_and_after=True))
                    reports.append(dict(model=model,opponent=opponent,report=str(report),sha256=helper.sha(report),summary=summary));write(root/'PROGRESS.json',dict(DEV=reports));resources(root,model+'/'+opponent+'/after')
            assert not ACTIVE and all(helper.sha(p)==h for p,h in frozen.items())
        partial['DEV']=reports;paths=set();audit=independent.review_dev(root,partial,paths)
        write(root/'DEV-RAW-AUDIT.json',dict(passed=True,DEV=audit,raw_artifact_sha256={str(p):helper.sha(p) for p in sorted(paths)},new_native_games=0,GPU_operations=0,optimizer_steps=0))
        write(root/'RESULT.partial.json',dict(passed=True,DEV=reports));write(root/'RESULT.json',dict(passed=True,DEV=reports,pending_full_CPU_replay=True))
        code=subprocess.run([str(LAB/'venv/bin/python'),str(HERE/'replay_dev.py'),'--dev-run',str(root),'--out',str(root/'DEV-NN-REPLAY')]).returncode
        assert code==0,'Independent full CPU replay failed; do not rerun games'
        result.update(passed=True,DEV=reports,unique_native_games=96,full_CPU_replay=True,raw_audit=True,pending_full_CPU_replay=False)
    except BaseException as error:result.update(error=repr(error),DEV=reports)
    finally:write(root/'RESULT.json',result)
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
