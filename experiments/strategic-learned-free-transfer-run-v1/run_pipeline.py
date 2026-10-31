"""Plan by default; explicitly executed by root only. Eight cells then the unchanged PPO update."""
import argparse,json,subprocess,sys
from pathlib import Path
from pipeline_common import HERE,BASE,LAB,AUDITOR,DEFAULT_CAPSULE,DEFAULT_INITIAL,INITIAL_SHA,MAPS,EPOCH,sha,source_inputs,capsule_inputs,validate_cells,clean_environment
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def jobs(seed_base):
    return [dict(map=m,opponent=o,player=p,seed=seed_base+i,logical_update=0)
            for i,(m,o,p) in enumerate((m,o,p) for m in MAPS for o in ('EmptyAI','Nullkiller2') for p in (0,1))]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--capsule',type=Path,default=DEFAULT_CAPSULE);parser.add_argument('--checkpoint',type=Path,default=DEFAULT_INITIAL)
    parser.add_argument('--seed-base',type=int,required=True);parser.add_argument('--seconds',type=float,default=120)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--collect-only',action='store_true')
    a=parser.parse_args();assert a.seconds>0;clean_environment()
    checkpoint=a.checkpoint.resolve();capsule=a.capsule.resolve();assert sha(checkpoint)==INITIAL_SHA,'Exploration batch must use the registered build-offset initialization'
    inputs=source_inputs()+capsule_inputs(capsule)+[Path(__file__).resolve(),BASE/'train_update_v3.py',checkpoint]
    frozen={str(p):sha(p) for p in inputs};a.out.mkdir(parents=True,exist_ok=False)
    commands=[];admissions=[]
    for i,job in enumerate(jobs(a.seed_base)):
        cell=a.out/f'cell-{i:02d}';run=cell/'native';audit=cell/'raw-audit';admission=cell/'admitted';admissions.append(admission)
        collect=['/usr/bin/python3',str(HERE/'collect_episode_v5.py'),'--capsule',str(capsule),'--checkpoint',str(checkpoint),
                 '--map',job['map'],'--opponent',job['opponent'],'--player',str(job['player']),'--seed',str(job['seed']),
                 '--logical-update','0','--seconds',str(a.seconds),'--out',str(run)]
        raw=[str(LAB/'venv/bin/python'),str(AUDITOR/'audit_game_v6.py'),str(run),str(audit)]
        admit=[str(LAB/'gpu-venv/bin/python'),str(BASE/'admit_episode_v5.py'),'--run',str(run),'--native-audit',str(audit/'AUDIT.json'),'--out',str(admission)]
        commands.append(dict(cell=i,job=job,commands=[collect,raw,admit]))
    train=[str(LAB/'gpu-venv/bin/python'),str(BASE/'train_update_v3.py'),'--initialize',str(checkpoint),'--capsule',str(capsule),
           '--purpose','curriculum_training','--seed',str(a.seed_base),'--out',str(a.out/'update-01')]
    for directory in admissions:train+=['--admission',str(directory)]
    plan=dict(epoch=EPOCH,execute=a.execute,collect_only=a.collect_only,checkpoint=str(checkpoint),checkpoint_sha256=INITIAL_SHA,
              capsule=str(capsule),jobs=commands,training_command=train,input_sha256=frozen,optimizer_reset=True,
              logical_update=0,parallelism=1,source_scope='Schema5 real build integration; original terminal reward/PPO unchanged; no partial-cell update')
    write(a.out/'PLAN.json',plan)
    if not a.execute:print(json.dumps({'plan_only':True,'cells':8,'optimizer_steps':0}));return 0
    completed=[]
    try:
        for item,directory in zip(commands,admissions):
            assert all(sha(Path(p))==h for p,h in frozen.items());directory.parent.mkdir()
            for stage,argv in zip(('collect','audit','admit'),item['commands']):
                result=subprocess.run(argv,capture_output=True,text=True)
                (directory.parent/(stage+'.log')).write_text(result.stdout+'\nSTDERR:\n'+result.stderr)
                assert result.returncode==0,f'cell{item["cell"]}/{stage} failed; no update'
            episode=json.loads((directory/'episode.json').read_text());report=json.loads((directory/'AUDIT.json').read_text())
            assert report['passed'] and episode['checkpoint_sha256']==INITIAL_SHA and episode['job']['logical_update']==0
            completed.append(episode);write(a.out/'PROGRESS.json',dict(completed=completed,optimizer_steps=0))
        validate_cells(completed);assert all(sha(Path(p))==h for p,h in frozen.items())
        if a.collect_only:
            write(a.out/'RESULT.json',dict(passed=True,collected=True,episodes=completed,optimizer_steps=0));return 0
        result=subprocess.run(train,capture_output=True,text=True);(a.out/'train.log').write_text(result.stdout+'\nSTDERR:\n'+result.stderr)
        assert result.returncode==0,'Training failed; preserve the original partial checkpoint/report'
        write(a.out/'RESULT.json',dict(passed=True,episodes=completed,training_result=str(a.out/'update-01/RESULT.json'),ability_improvement_claim=False));return 0
    except BaseException as error:
        write(a.out/'RESULT.json',dict(passed=False,error=repr(error),completed=completed,complete_curriculum=False,ability_improvement_claim=False));return 1
if __name__=='__main__':raise SystemExit(main())

