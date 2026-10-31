"""Reviewable controller: plan-only unless explicitly --execute; owns all leases."""
import argparse,fcntl,importlib.util,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;R=ROOT/'research';OLD=ROOT/'experiments/battle-training-continuation-20261020';LAB=Path('/root/heroes3-ai-lab');sys.path[:0]=[str(HERE),str(R)];sys.path.append(str(OLD))
import restore_learner as restore
import leases
from lab_io import atomic_json
def inputs():
    spec=importlib.util.spec_from_file_location('_old_freeze',OLD/'run.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    old.PARENT=LAB/'evaluations/battle-diverse60-native-02/models/1792504676114060650/update-30.pt';old.PARENT_SHA='dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa';frozen=old.inputs()
    for p in HERE.iterdir():
        if p.is_file():frozen[str(p)]=restore.sha(p)
    frozen[str(restore.DEFAULT_CHECKPOINT)]=restore.DEFAULT_SHA
    return frozen
def command(out,arm,start,stop,checkpoint,expected,freeze,qualify=False):
    result=['bash',str(R/'run-lab.sh'),str(HERE/'train.py'),'--checkpoint',str(checkpoint),'--expected-sha',expected,'--freeze',str(freeze),'--out',str(out),'--arm',arm,'--phase-start',str(start),'--phase-stop',str(stop)]
    return result+(['--qualify'] if qualify else [])
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--evaluate',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    assert restore.sha(restore.DEFAULT_CHECKPOINT)==restore.DEFAULT_SHA
    frozen=dict(schema='terminal-drain-prefix-credit-v1',input_sha256=inputs());atomic_json(a.out/'FREEZE.json',frozen)
    atomic_json(a.out/'PLAN.json',dict(schema=frozen['schema'],parent_checkpoint=str(restore.DEFAULT_CHECKPOINT),parent_sha256=restore.DEFAULT_SHA,parent_Adam=7680,registered_curriculum=str(HERE/'REGISTERED_CURRICULUM.json'),admitted_per_arm=4096,suffix_per_arm=4096,native_per_arm=8192,planned_Adam_per_arm=1024,global_updates=list(range(61,69)),evaluation=a.evaluate,DEV_games=96,DEV_seed_base=2026107600,execute=a.execute))
    if not a.execute:print(json.dumps(dict(plan_only=True,path=str(a.out/'PLAN.json'))));return 0
    assert all(os.environ.get(k) in (None,'','0') for k in ['LAB_NATIVE_ONNX_CUDA','LAB_ONNX_CUDA','LAB_BATTLEAI_TEACHER'])
    env=dict(os.environ,LAB_PYTHON=str(LAB/'gpu-venv/bin/python'),LAB_STAGED_BOOT='1',LAB_WORKER_ROOT=str(LAB/'workers'/(a.out.name+'-bootstrap')),CUBLAS_WORKSPACE_CONFIG=':4096:8',TERMINAL_CREDIT_LEASE_OWNER='1')
    handles=[];result=dict(passed=False,qualification=False,arms={},ability_promotion=False)
    def invoke(name,arm,start,stop,cp,sha,qualify=False):
        out=a.out/name
        with (a.out/(name+'.log')).open('w') as stream:code=leases.run_owned(command(out,arm,start,stop,cp,sha,a.out/'FREEZE.json',qualify),env=env,stream=stream,pass_fds=[h.fileno() for h in handles])
        assert code==0,name+' failed: preserve evidence, no retry'
        d=json.loads((out/'RESULT.json').read_text());assert d['passed'] and d['normal_workers_shutdown']
        if qualify:assert d['qualified'] and d['actual_Adam_steps']==7680 and d['new_Adam_steps']==0 and d['total_native_stage_rows']==2048 and d['admitted_stage_rows']==0
        else:
            assert [x['update'] for x in d['records']]==list(range(61+start*2,61+stop*2)) and all(x['actual_Adam']==128 for x in d['records'])
            assert d['actual_Adam_steps']==7680+256*stop and d['admitted_stage_rows']==d['suffix_stage_rows']==1024*stop and d['total_native_stage_rows']==2048*stop
        assert all(restore.sha(p)==h for p,h in frozen['input_sha256'].items())
        with (a.out/(name+'-audit.log')).open('w') as stream:audit_code=leases.run_owned([str(LAB/'venv/bin/python'),str(HERE/'audit.py'),'--stage',str(out)],env=env,stream=stream,pass_fds=[h.fileno() for h in handles])
        assert audit_code==0 and json.loads((out/'AUDIT.json').read_text())['passed'],name+' independent raw/target audit failed'
        return d
    try:
        for name in ['.gpu-learner-lock','.pool-lock']:
            h=(LAB/'evaluations'/name).open('a');fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(h)
        env['TERMINAL_CREDIT_LEASES']=json.dumps([leases.metadata(h,path) for h,path in zip(handles,leases.PATHS)])
        invoke('qualification','control',0,1,restore.DEFAULT_CHECKPOINT,restore.DEFAULT_SHA,True);result['qualification']=True;atomic_json(a.out/'RESULT.partial.json',result)
        micro={}
        for arm in ['control','candidate']:
            micro[arm]=invoke(arm+'-micro',arm,0,1,restore.DEFAULT_CHECKPOINT,restore.DEFAULT_SHA)
        assert micro['control']['actual_Adam_steps']==micro['candidate']['actual_Adam_steps']==7936
        latest=dict(micro)
        for phase in range(1,4):
            for arm in ['control','candidate']:
                previous=latest[arm];d=invoke(arm+'-phase-'+str(phase),arm,phase,phase+1,Path(previous['checkpoint']),previous['checkpoint_sha256']);latest[arm]=d
                result['arms'][arm]=dict(checkpoint=d['checkpoint'],checkpoint_sha256=d['checkpoint_sha256'],actual_Adam_steps=d['actual_Adam_steps'],new_Adam_steps=d['actual_Adam_steps']-7680,admitted_stage_rows=d['admitted_stage_rows'],suffix_stage_rows=d['suffix_stage_rows'],native_stage_rows=d['total_native_stage_rows'])
                atomic_json(a.out/'RESULT.partial.json',result)
            assert latest['control']['actual_Adam_steps']==latest['candidate']['actual_Adam_steps']==7680+256*(phase+1),'Paired phase budget mismatch'
        for h in reversed(handles):h.close()
        handles=[]
        if a.evaluate:
            with (a.out/'DEV-controller.log').open('w') as stream:code=leases.run_owned([str(LAB/'venv/bin/python'),str(HERE/'evaluate.py'),'--run',str(a.out)],env=env,stream=stream)
            assert code==0,'DEV invalid, no retrain'
            result['DEV']=json.loads((a.out/'DEV-RESULT.json').read_text())['DEV']
        result['passed']=True
    except BaseException as error:result['error']=repr(error)
    finally:
        leases.finish_owned_groups()
        for h in reversed(handles):h.close()
        atomic_json(a.out/'RESULT.json',result)
    print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
