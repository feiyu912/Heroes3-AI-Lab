"""Only candidate57's remaining three updates; control60 is immutable."""
import argparse,fcntl,importlib.util,json,os,subprocess,sys
from pathlib import Path
import restore_learner as restore
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'battle-training-continuation-20261020'
spec=importlib.util.spec_from_file_location('original_battle_plan',OLD/'run.py')
original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
PARENT=Path('/root/heroes3-ai-lab/evaluations/battle-diverse60-native-02/models/1792504676114060650/update-30.pt')
PARENT_SHA='dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa'
CONTROL=OLD/'monitor-independent-01/user-pause-01/control-update-60.pt'
CONTROL_SHA='443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20'
original.PARENT=PARENT;original.PARENT_SHA=PARENT_SHA
sha=restore.sha
def write(path,payload):path.write_text(json.dumps(payload,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--evaluate',action='store_true');p.add_argument('--restore-proof',type=Path);a=p.parse_args()
    assert all(os.environ.get(k) in (None,'','0') for k in ['LAB_NATIVE_ONNX_CUDA','LAB_ONNX_CUDA','LAB_BATTLEAI_TEACHER'])
    assert sha(CONTROL)==CONTROL_SHA and sha(restore.DEFAULT_CHECKPOINT)==restore.DEFAULT_SHA and sha(PARENT)==PARENT_SHA
    proof=None
    if a.restore_proof:
        proof=json.loads(a.restore_proof.read_text())
        assert all(proof[k] is True for k in ['passed_exact','CUDA_restore_executed','model_Adam_named_binding_exact','CPU_CUDA_Python_NumPy_RNG_exact','invalid_resume_preserves_model_Adam_all_RNG_counter'])
        assert proof['checkpoint_sha256']==restore.DEFAULT_SHA and proof['actual_Adam_counter_restored']==7296
        assert proof['audit_optimizer_steps']==proof['new_native_games']==0
        assert proof['helper_sha256']==sha(HERE/'restore_learner.py') and proof['auditor_sha256']==sha(HERE/'audit_restore_cuda.py')
    if a.execute:assert proof,'Actual candidate57 CUDA restoration proof required'
    a.out.mkdir(parents=True,exist_ok=False);out=a.out/'candidate';out.mkdir()
    frozen=original.inputs()
    frozen.update({str(x):sha(x) for x in HERE.iterdir() if x.is_file() and x.suffix in ('.py','.md','.json')})
    frozen[str(CONTROL)]=sha(CONTROL)
    frozen[str(restore.DEFAULT_CHECKPOINT)]=restore.DEFAULT_SHA
    for x in [OLD/'final-independent-01/audit_final.py',HERE.parent/'battle-diverse-curriculum-20261020/final-independent-01/audit_final.py']:
        frozen[str(x)]=sha(x)
    if a.restore_proof:frozen[str(a.restore_proof.resolve())]=sha(a.restore_proof)
    freeze=dict(schema='battle-candidate57-resume-v1',input_sha256=frozen)
    write(out/'FREEZE.json',freeze)
    command=original.training(out,'candidate');command[2]=str(HERE/'train_last_graph.py')
    command[command.index('--checkpoint')+1]=str(restore.DEFAULT_CHECKPOINT)
    command[command.index('--updates')+1]='3'
    plan=dict(command=command,parent_checkpoint=str(PARENT),checkpoint_sha256=restore.DEFAULT_SHA,restored_updates=57,restored_environment_steps=29184,restored_Adam_steps=7296,
        final_updates=60,new_transitions=1536,new_expected_Adam_steps=384,final_expected_Adam_steps=7680,control_unchanged_sha256=CONTROL_SHA,
        phase_schedule=[13,14,14],native_boundary='Fresh native phase13 for update58, seed base2026105800+phase*1000+slot; phase14 original seeds. Inflight state discarded, not terminal/loss.',
        limitation='Candidate has one extra native restart relative to control; resumed result cannot establish a pure uninterrupted LR causal effect.',
        DEV_unique_games=96,DEV_indices=list(range(192,200)),DEV_seed_base=2026103600,evaluation=a.evaluate)
    write(a.out/'PLAN.json',plan)
    if not a.execute:print(json.dumps(dict(plan_only=True,path=str(a.out/'PLAN.json'))));return
    handles=[];result=dict(passed=False,ability_improvement_claim=False,control_retrained=False)
    env=dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',LAB_STAGED_BOOT='1',LAB_WORKER_ROOT='/root/heroes3-ai-lab/workers/'+a.out.name+'-bootstrap')
    try:
        for name in ['.gpu-learner-lock','.pool-lock']:
            h=(original.LAB/'evaluations'/name).open('a');fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(h)
        with (out/'training.log').open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
        assert r.returncode==0,'Training failed, preserve partial evidence'
        t=json.loads((out/'training.json').read_text());records=t['records']
        assert t['completed'] and t['all_workers_exit_zero'] and [r['update'] for r in records]==[58,59,60]
        assert [r['phase'] for r in records]==[13,14,14] and all(r['samples']==512 and r['checkpoint_readback']['Adam_exact'] for r in records)
        assert records[-1]['actual_Adam_steps_total']==7680 and t['stage_actual_Adam_steps']==384
        restored=t['restoration'];assert restored['CUDA_restore_executed'] and restored['actual_Adam_counter_before_first_sampling']==7296 and all(restored['all_RNG_before_first_sampling'].values())
        result['candidate']=dict(checkpoint=t['checkpoint'],sha256=sha(t['checkpoint']),new_Adam_steps=384,cumulative_Adam_steps=7680)
        assert all(sha(x)==h for x,h in frozen.items())
        for h in reversed(handles):h.close()
        handles=[]
        if a.evaluate:
            env['LAB_PYTHON']='/root/heroes3-ai-lab/venv/bin/python';result['DEV']=[]
            for name,checkpoint in [('parent30',PARENT),('control',CONTROL),('candidate',Path(t['checkpoint']))]:
                for opponent in ['BattleAI','MMAI_MODEL']:
                    command=original.evaluate(a.out,name,checkpoint,opponent)
                    with (a.out/(name+'-'+opponent+'-DEV.log')).open('w') as log:r=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
                    assert r.returncode==0,'DEV invalid '+name+'/'+opponent
                    path=Path(command[command.index('--output')+1]);d=json.loads(path.read_text());s=d['summary'][0]
                    assert s['battles']==16 and s['truncated']==s['non_normal_terminations']==s['invalid_actions']==0
                    result['DEV'].append(dict(model=name,opponent=opponent,report=str(path),sha256=sha(path),summary=s))
                    write(a.out/'RESULT.partial.json',result)
        assert all(sha(x)==h for x,h in frozen.items());result['passed']=True
    except BaseException as error:result['error']=repr(error)
    finally:
        for h in reversed(handles):h.close()
        write(a.out/'RESULT.json',result)
    print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
