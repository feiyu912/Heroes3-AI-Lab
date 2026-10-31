"""Sequential follow-up experiments; no final-test results used for selection."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from goal_training_recovery import resume_command,annotate,snapshot
from lab_io import atomic_json
from goal_selection import score as goal_score

r=Path('/mnt/g/Heroes3-AI-Lab/research')
control=r/'goal-v5-control.json'
rows=[]


def write_state(state,**detail):
    atomic_json(control,dict(state=state,updated_unix=time.time(),**detail))


def run(command,log,timeout=86400,env=None):
    if (r/log).exists():
        (r/log).rename(r/(log+'.previous-'+str(time.time_ns())))
    with (r/log).open('wb') as stream:
        process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,env=env)
    assert process.returncode==0,f'{log}: exit {process.returncode}; inspect log before continuing'


def evaluate(checkpoint,name,policy='recovered',mode='heads'):
    iteration=int(Path(checkpoint).stem.split('-')[-1]) if Path(checkpoint).stem.startswith('update-') else 0
    row=dict(name=name,checkpoint=checkpoint,policy=policy,iteration=iteration,finetuning_mode=mode)
    for scenario_file,indices,seeds,prefix in [('scenarios-v2.json',range(20,26),4,''),
                                             ('diverse-curriculum.json',range(192,204),2,'development_')]:
        for opponent,label in [('BattleAI',''),('MMAI_MODEL','upstream_')]:
            output=r/f'{name}-{prefix}{label}validation.json'
            if output.exists() and json.loads(output.read_text())['checkpoint']!=checkpoint:
                output.rename(output.with_name(output.name+'.previous-'+str(time.time_ns())))
            if not output.exists():
                command=['python3',str(r/'evaluate-battles.py'),'--checkpoint',checkpoint,'--policies',policy,
                    '--scenario-file',str(r/scenario_file),'--scenarios',*map(str,indices),'--seeds',str(seeds),
                    '--workers','12','--opponent',opponent,'--output',str(output)]
                if opponent=='MMAI_MODEL':command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
                run(command,output.stem+'.log',3600)
            data=json.loads(output.read_text())
            assert data['checkpoint']==checkpoint and data['summary'][0]['battles']==48
            row[prefix+label+'validation_report']=str(output)
            row[prefix+label+'validation']=data['summary'][0]
    rows.append(row)
    atomic_json(r/'goal-v5-validation.json',rows)
    print('Validated',name,'score',score(row),flush=True)
    return row


def score(row):
    return goal_score(row)


def train(name,checkpoint,mode,updates,**extra):
    output=r/(name+'.json')
    if output.exists():
        existing=json.loads(output.read_text())
        checkpoint=existing.get('experiment_initial_checkpoint',existing['config'].get('experiment_initial_checkpoint',existing['config']['checkpoint']))
        print('Preserving existing experiment initialization',name,checkpoint,flush=True)
    command=['bash',str(r/'run-lab.sh'),str(r/('train-recovered-heads.py' if mode=='heads' else 'train-graph-finetune.py')),
        '--checkpoint',checkpoint,'--output',str(output),'--workers','24','--updates',str(updates),'--rollout','32',
        '--seed',str(extra.pop('seed',20261020)),'--scenario-file',str(r/'diverse-curriculum.json'),
        '--shaping','.5','--step-cost','.002','--opponents','BattleAI','MMAI_MODEL']
    if mode=='heads':command+=['--balanced-configs','--learning-rate','0.00005','--entropy-coef','0.005']
    else:command+=['--mode',mode,'--microbatch',str(extra.pop('microbatch',4))]
    for key,value in extra.items():command+=['--'+key.replace('_','-'),str(value)]
    command,history,completed=resume_command(command,output,checkpoint,updates)
    if completed:return completed
    write_state('training',experiment=name,mode=mode,updates=updates,workers=24)
    run(command,name+'.log',86400,dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',LAB_STAGED_BOOT='1'))
    data=annotate(output,checkpoint,history);assert data['completed'] and data['all_workers_exit_zero']
    return data


try:
    write_state('waiting_for_restored_stage',workers=24)
    while True:
        progress=json.loads((r/'challenge24-pipeline-progress.json').read_text())
        assert all(x['returncode']==0 for x in progress),'Restored pipeline failed'
        if len(progress)>=3:break
        time.sleep(15)
    # At this point the original pipeline is waiting in select-challenge-final.
    write_state('validating_baselines')
    initial='/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt'
    evaluate(initial,'v5-public-original',mode='unchanged')
    previous=json.loads((r/'selected-trained-model.json').read_text())['checkpoint']
    evaluate(previous,'v5-lab-v3',policy='model',mode='lab-gnn')
    adapted=json.loads((r/'recovered-adaptation-validation.json').read_text())
    best_adapted=max(adapted,key=lambda x:(min(x['validation']['win_rate'],x['upstream_validation']['win_rate']),x['validation']['win_rate']+x['upstream_validation']['win_rate']))
    evaluate(best_adapted['checkpoint'],'v5-restored-best-heads')
    # Real CUDA graph-training capacity check, deliberately excluded as a contender.
    probe=r/'v5-full-graph-capacity.json'
    if not probe.exists() or not json.loads(probe.read_text()).get('completed'):
        run(['bash',str(r/'run-lab.sh'),str(r/'train-graph-finetune.py'),'--checkpoint',initial,
             '--mode','last','--workers','24','--updates','2','--rollout','8','--microbatch','4','--output',str(probe)],
            'v5-full-graph-capacity.log',1800,dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',LAB_STAGED_BOOT='1'))
    assert json.loads(probe.read_text())['completed']
    data=train('v5-diverse-heads',initial,'heads',256)
    folder=Path(data['checkpoint']).parent
    for iteration in [128,256]:
        row=evaluate(snapshot(data,iteration),f'v5-diverse-heads-{iteration}')
        row['iteration']=iteration
    start=max((x for x in rows if x['policy']=='recovered'),key=score)['checkpoint']
    data=train('v5-diverse-last',start,'last',128,seed=20261021)
    folder=Path(data['checkpoint']).parent
    for iteration in [64,128]:
        row=evaluate(snapshot(data,iteration),f'v5-diverse-last-{iteration}',mode='last')
        row['iteration']=iteration
    start=max((x for x in rows if x['policy']=='recovered'),key=score)['checkpoint']
    data=train('v5-diverse-all',start,'all',128,seed=20261022,microbatch=2,learning_rate=.000003,head_learning_rate=.00002)
    folder=Path(data['checkpoint']).parent
    for iteration in [64,128]:
        row=evaluate(snapshot(data,iteration),f'v5-diverse-all-{iteration}',mode='all')
        row['iteration']=iteration
    best=max(rows,key=score)
    best['selection']='Validation only: maximize worst normalized goal progress across old/diverse sets (BattleAI rate/.95; author scenario-cluster95 lower/.50), then BattleAI sum, author lower bound, author sum and lower casualties. Final test never inspected; final success thresholds unchanged.'
    best['validation_score']=score(best)
    (r/'goal-v5-validation.json').write_text(json.dumps(rows,indent=2))
    (r/'goal-v5-selection.json').write_text(json.dumps(best,indent=2))
    write_state('experiments_complete',selected=best['name'],score=score(best),workers=24)
    print('Extended experiments complete',best['name'],score(best),flush=True)
except BaseException as error:
    write_state('failed',error=repr(error))
    raise
