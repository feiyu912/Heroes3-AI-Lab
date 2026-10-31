"""Plan by default. Root alone explicitly executes under GPU/pool leases."""
import argparse,collections,fcntl,hashlib,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;R=HERE.parent.parent/'research';LAB=Path('/root/heroes3-ai-lab')
B64=LAB/'models/graph-finetune/1792068859379237126/update-64.pt';SCENARIOS=R/'diverse-curriculum.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def inputs():
    gym=LAB/'src/gym';runtime=gym/'vcmi/rel/bin'
    paths=set(HERE.glob('*.py'))|set(R.glob('*.py'))|set(R.glob('*.sh'))|{HERE/'PLAN.md',B64,SCENARIOS}
    paths.update(runtime/n for n in ['libvcmi.so','libmlclient.so','libmlserverplugin.so'])
    paths.update(gym/'vcmi_gym/connectors/rel'/n for n in ['connector_v15.so','exporter_v15.so'])
    paths.update(gym/'vcmi_gym/envs/v15'/n for n in ['vcmi_env.py','pyconnector.py','decode.py'])
    paths.add(LAB/'onnxruntime/lib/libonnxruntime.so');paths.add(LAB/'data/vcmi/Mods/ML/Content/heroes.json')
    paths.update(LAB/'data/vcmi/Data/MMAI/models'/('lab-upstream-'+role+'.onnx') for role in ['attacker','defender'])
    cases=json.loads(SCENARIOS.read_text());assert len([c for c in cases if c['split']=='train'])==192
    for c in cases:
        p=LAB/'data/vcmi/Maps'/c['map'];assert c['sha256']==sha(p);paths.add(p)
    return {str(p):sha(p) for p in sorted(paths)}
def training(out):
    return ['bash',str(R/'run-lab.sh'),str(HERE/'train_last_graph.py'),'--checkpoint',str(B64),'--output',str(out/'training.json'),
        '--models-dir',str(out/'models'),'--freeze',str(out/'FREEZE.json'),'--mode','last','--workers','8','--updates','4','--rollout','32',
        '--epochs','2','--microbatch','8','--no-auto-microbatch','--learning-rate','1e-6','--head-learning-rate','1e-5',
        '--gamma','1','--step-cost','0','--shaping','.5','--entropy-coef','.005','--seed','2026102008',
        '--native-opponent-device','cpu','--first-battle','--rotate-every','16','--opponents','BattleAI','MMAI_MODEL',
        '--scenario-file',str(SCENARIOS)]
def evaluate(out,name,checkpoint,opponent):
    command=['bash',str(R/'run-lab.sh'),str(HERE/'evaluate_bounded.py'),'--checkpoint',str(checkpoint),'--policies','recovered',
        '--scenario-file',str(SCENARIOS),'--scenarios',*map(str,range(192,200)),'--seeds','1','--seed-base','2026102500',
        '--workers','8','--opponent',opponent,'--output',str(out/(name+'-'+opponent+'-DEV.json'))]
    if opponent=='MMAI_MODEL':command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
    return command
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');p.add_argument('--evaluate',action='store_true');a=p.parse_args()
    assert not any(os.environ.get(v) not in (None,'','0') for v in ['LAB_NATIVE_ONNX_CUDA','LAB_ONNX_CUDA','LAB_BATTLEAI_TEACHER'])
    a.out.mkdir(parents=True,exist_ok=False);frozen=dict(schema='battle-resume-bounded-last-v1',input_sha256=inputs())
    assert sha(B64)=='1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936'
    write(a.out/'FREEZE.json',frozen)
    plan=dict(schema=frozen['schema'],execute=a.execute,train_command=training(a.out),workers=8,updates=4,owned_transitions_budget=1024,
        optimizer='New Adam, B64 weights only',TRAIN_indices=list(range(192)),DEV_indices=list(range(192,200)),DEV_games=64,
        evaluation=a.evaluate,opponents=['BattleAI','MMAI_MODEL'],MMAI_GPU_used=False,expert_labels_used=False,
        native_environment_restorable=False,confirmation_v2_touched=False,freeze_sha256=sha(a.out/'FREEZE.json'))
    write(a.out/'PLAN.json',plan)
    if not a.execute:print(json.dumps(dict(plan_only=True,plan=str(a.out/'PLAN.json'),input_count=len(frozen['input_sha256']))));return 0
    env=dict(os.environ,LAB_PYTHON=str(LAB/'gpu-venv/bin/python'),LAB_STAGED_BOOT='1',LAB_WORKER_ROOT=str(LAB/'workers'/(a.out.name+'-bootstrap')))
    handles=[];result=dict(passed=False,training_completed=False,ability_improvement_claim=False)
    try:
        for name in ['.gpu-learner-lock','.pool-lock']:
            h=(LAB/'evaluations'/name).open('a');fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(h)
        with (a.out/'training.log').open('w') as stream:run=subprocess.run(plan['train_command'],env=env,stdout=stream,stderr=subprocess.STDOUT)
        assert run.returncode==0,'Training exited '+str(run.returncode)
        t=json.loads((a.out/'training.json').read_text());assert t['completed'] and t['all_workers_exit_zero'] and len(t['records'])==4
        assert all(r['actual_Adam_steps']>0 and r['checkpoint_readback']['Adam_exact'] for r in t['records'])
        assert all(sha(f)==h for f,h in frozen['input_sha256'].items())
        result.update(training_completed=True,checkpoint=t['checkpoint'],checkpoint_sha256=sha(t['checkpoint']),actual_Adam_steps=t['records'][-1]['actual_Adam_steps_total'])
        # Evaluation owns its own pool lock; release both learner leases first.
        for h in reversed(handles):h.close()
        handles=[]
        if a.evaluate:
            env['LAB_PYTHON']=str(LAB/'venv/bin/python');reports=[]
            for name,checkpoint in [('B64',B64),('update4',t['checkpoint'])]:
                for opponent in ['BattleAI','MMAI_MODEL']:
                    command=evaluate(a.out,name,checkpoint,opponent)
                    with (a.out/(name+'-'+opponent+'-DEV.log')).open('w') as stream:r=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT)
                    assert r.returncode==0,'DEV invalid '+name+'/'+opponent
                    report=Path(command[command.index('--output')+1]);d=json.loads(report.read_text());s=d['summary'][0]
                    assert s['battles']==16 and s['truncated']==s['non_normal_terminations']==s['invalid_actions']==0
                    reports.append(dict(model=name,opponent=opponent,report=str(report),sha256=sha(report),summary=s))
            result['DEV']=reports
        assert all(sha(f)==h for f,h in frozen['input_sha256'].items());result['passed']=True
    except BaseException as e:result['error']=repr(e)
    finally:
        for h in reversed(handles):h.close()
        write(a.out/'RESULT.json',result)
    print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
