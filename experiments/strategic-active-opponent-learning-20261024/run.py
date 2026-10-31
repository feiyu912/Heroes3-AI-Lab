"""Fixed two-treatment fresh on-policy TRAIN followed by separate 24-game DEV."""
import argparse,json,os,signal,sys
from pathlib import Path
import leases
from pipeline_common import HERE,BASE,LAB,MAPS,EPOCH,DEFAULT_INITIAL,INITIAL_SHA,DEFAULT_CAPSULE,source_inputs,capsule_inputs,sha,validate_cells,training_variant
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def resource_check(log,stage):
    values={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    row=dict(stage=stage,available_mib=values['MemAvailable']/1024,swap_used_mib=(values['SwapTotal']-values['SwapFree'])/1024)
    with log.open('a') as stream:stream.write(json.dumps(row)+'\n')
    assert row['available_mib']>2048 and row['swap_used_mib']<256,'Resource guard stopped stage: '+str(log)
def interrupted(signum,frame):raise KeyboardInterrupt('Controller interrupted '+str(signum))
signal.signal(signal.SIGTERM,interrupted)
def jobs():
    return [dict(map=m,opponent=o,player=p,seed=2026104400+i,logical_update=0) for i,(m,o,p) in enumerate((m,o,p) for m in MAPS for o in ('EmptyAI','Nullkiller2') for p in (0,1))]
def run_command(command,log):
    resource_check(log.with_suffix('.resources.jsonl'),'before')
    with log.open('w') as stream:code=leases.run_owned(command,env=dict(os.environ),stream=stream)
    assert code==0,'Stage failed; preserve without retry: '+str(log)
    resource_check(log.with_suffix('.resources.jsonl'),'after')
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    assert sha(DEFAULT_INITIAL)==INITIAL_SHA
    freeze=json.loads((HERE/'SOURCE_FREEZE.json').read_text())
    assert all(sha(path)==h for path,h in freeze['files'].items())
    inputs=source_inputs()+capsule_inputs(DEFAULT_CAPSULE)+[DEFAULT_INITIAL,HERE/'SOURCE_FREEZE.json']
    frozen={str(path):sha(path) for path in inputs};a.out.mkdir(parents=True,exist_ok=False)
    arms={};commands=[]
    for arm in ('control','curriculum'):
        admissions=[];cells=[]
        for i,job in enumerate(jobs()):
            root=a.out/arm/f'cell-{i:02d}';admissions.append(root/'admitted')
            cells.append(dict(job=job,variant=training_variant(job['map'],job['player'],job['opponent'],arm),root=str(root),commands=[
                ['/usr/bin/python3',str(HERE/'collect_episode_v5.py'),'--capsule',str(DEFAULT_CAPSULE),'--checkpoint',str(DEFAULT_INITIAL),'--arm',arm,'--map',job['map'],'--opponent',job['opponent'],'--player',str(job['player']),'--seed',str(job['seed']),'--logical-update','0','--seconds','120','--out',str(root/'native')],
                [str(LAB/'venv/bin/python'),str(HERE/'audit_game_v6.py'),str(root/'native'),str(root/'raw-audit')],
                [str(LAB/'gpu-venv/bin/python'),str(BASE/'admit_episode_v5.py'),'--run',str(root/'native'),'--native-audit',str(root/'raw-audit/AUDIT.json'),'--out',str(root/'admitted')]]))
        train=[str(LAB/'gpu-venv/bin/python'),str(BASE/'train_update_v3.py'),'--initialize',str(DEFAULT_INITIAL),'--capsule',str(DEFAULT_CAPSULE),'--arm',arm,'--purpose','curriculum_training','--seed','2026104400','--out',str(a.out/arm/'update-01')]
        for directory in admissions:train+=['--admission',str(directory)]
        commands.append(dict(arm=arm,cells=cells,train=train))
    write(a.out/'PLAN.json',dict(epoch=EPOCH,commands=commands,input_sha256=frozen,execute=a.execute,scientific_plan_sha256=sha(HERE/'PLAN.md'),final_test_touched=False))
    if not a.execute:print(json.dumps(dict(plan_only=True,new_training_games=16,DEV_games=24,optimizer_steps=0)));return 0
    result=dict(passed=False,arms=arms,final_test_touched=False,model_promoted=False)
    try:
        for treatment in commands:
            arm=treatment['arm'];completed=[]
            for i,cell in enumerate(treatment['cells']):
                assert all(sha(path)==h for path,h in frozen.items());root=Path(cell['root']);root.mkdir(parents=True)
                for stage,command in zip(('collect','audit','admit'),cell['commands']):run_command(command,root/(stage+'.log'))
                completed.append(json.loads((root/'admitted/episode.json').read_text()))
                write(a.out/'PROGRESS.json',dict(arm=arm,completed=completed,finished_arms=arms))
            validate_cells(completed);run_command(treatment['train'],a.out/arm/'train.log')
            learned=json.loads((a.out/arm/'update-01/RESULT.json').read_text());assert learned['completed_update']
            recovery=a.out/arm/'recovery-audit'
            run_command([str(LAB/'gpu-venv/bin/python'),str(HERE/'audit_checkpoint_cuda.py'),'--checkpoint',learned['checkpoint'],'--capsule',str(DEFAULT_CAPSULE),'--out',str(recovery)],a.out/arm/'recovery.log')
            arms[arm]=dict(episodes=completed,training=learned,recovery=str(recovery/'AUDIT.json'))
            write(a.out/'PROGRESS.json',dict(finished_arms=arms))
        assert all(sha(path)==h for path,h in frozen.items())
        command=[str(LAB/'venv/bin/python'),str(HERE/'evaluate_dev.py'),'--control',arms['control']['training']['checkpoint'],'--curriculum',arms['curriculum']['training']['checkpoint'],'--out',str(a.out/'DEV'),'--execute']
        run_command(command,a.out/'DEV.log');result.update(passed=True,DEV=str(a.out/'DEV/RESULT.json'))
    except BaseException as error:result['error']=repr(error)
    finally:leases.finish_owned_groups()
    write(a.out/'RESULT.json',result);print(json.dumps(dict(passed=result['passed'],error=result.get('error'),finished_arms=list(arms))))
    return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
