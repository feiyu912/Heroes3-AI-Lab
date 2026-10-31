"""Plan-only by default. Exactly twelve registered TRAIN calibration cells."""
import argparse,json,subprocess
from pathlib import Path
from pipeline_common import HERE,LAB,EPOCH,INITIAL_SHA,DEFAULT_INITIAL,DEFAULT_CAPSULE,source_inputs,capsule_inputs,map_manifest,sha,validate_native_epoch
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def jobs():
    manifest=map_manifest();result=[]
    for multiplier in (1,2,4):
        for index,name in enumerate(('takeover-v2-train-01-mines','takeover-v2-train-02-development')):
            for player in (0,1):
                entry=next(e for e in manifest['variants'] if e['source_map']==name and e['owned_player']==player and e['multiplier']==multiplier)
                result.append(dict(map=entry['map'],source_map=name,player=player,multiplier=multiplier,seed=2026104300+2*index+player,opponent='Nullkiller2'))
    return result
def select_difficulty(results):
    if len(results)!=12 or not all(r['valid'] for r in results):return dict(qualified=False,selected_multiplier=None,reason='Complete twelve valid native games required; invalid/timeout is unscored')
    wins={multiplier:sum(r['win'] for r in results if r['job']['multiplier']==multiplier) for multiplier in (1,2,4)}
    selected=next((multiplier for multiplier in (2,4) if wins[multiplier]>=2),None)
    return dict(qualified=selected is not None,selected_multiplier=selected,wins_by_multiplier=wins,criterion='first boosted level x2 then x4 with at least2/4 normal-terminal NK wins',
        reason='Registered threshold met' if selected else 'No registered boost qualified; no grid or seed expansion')
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--checkpoint',type=Path,default=DEFAULT_INITIAL)
    p.add_argument('--capsule',type=Path,default=DEFAULT_CAPSULE);p.add_argument('--seconds',type=float,default=120);p.add_argument('--execute',action='store_true');a=p.parse_args()
    assert a.seconds>0 and sha(a.checkpoint)==INITIAL_SHA
    inputs=source_inputs()+capsule_inputs(a.capsule)+[a.checkpoint,a.checkpoint.parent/'AUDIT.json'];frozen={str(path):sha(path) for path in inputs}
    registered=jobs();assert len(registered)==12;a.out.mkdir(parents=True,exist_ok=False)
    commands=[]
    for i,job in enumerate(registered):
        root=a.out/f'cell-{i:02d}'
        collect=['/usr/bin/python3',str(HERE/'collect_calibration.py'),'--capsule',str(a.capsule),'--checkpoint',str(a.checkpoint),'--map',job['map'],
            '--player',str(job['player']),'--opponent','Nullkiller2','--seed',str(job['seed']),'--seconds',str(a.seconds),'--out',str(root/'native')]
        audit=[str(LAB/'venv/bin/python'),str(HERE/'audit_game.py'),str(root/'native'),str(root/'raw-audit')]
        commands.append(dict(cell=i,job=job,commands=[collect,audit]))
    write(a.out/'PLAN.json',dict(epoch=EPOCH,execute=a.execute,jobs=commands,input_sha256=frozen,checkpoint_sha256=INITIAL_SHA,
        selection_rule='Run exactly12; select first x2 then x4 with >=2/4 real NK wins; original x1 is reference; otherwise unqualified',
        TRAIN_only=True,DEV_read=False,finaltest_touched=False,training_samples=0,optimizer_steps=0,expert_labels=0))
    if not a.execute:print(json.dumps(dict(plan_only=True,registered_games=12,native_runs=0,optimizer_steps=0)));return 0
    results=[]
    try:
        for item in commands:
            assert all(sha(path)==h for path,h in frozen.items());root=a.out/f"cell-{item['cell']:02d}";root.mkdir()
            for label,command in zip(('collect','audit'),item['commands']):
                run=subprocess.run(command,capture_output=True,text=True);(root/(label+'.log')).write_text(run.stdout+'\nSTDERR:\n'+run.stderr)
                assert run.returncode==0,'Invalid calibration cell; unscored '+str(root)
            native=json.loads((root/'raw-audit/AUDIT.json').read_text());plan=json.loads((root/'native/PLAN.json').read_text());execution=json.loads((root/'native/EXECUTION.json').read_text())
            validate_native_epoch(native,plan,execution);assert native['winner'] in ('red','blue')
            results.append(dict(job=item['job'],valid=True,win=native['winner']==('red' if item['job']['player']==0 else 'blue'),
                audit_sha256=sha(root/'raw-audit/AUDIT.json'),counts=native['counts'],initial_request_sha256=sha(root/'native/agent/request-00000001.json')))
            write(a.out/'PROGRESS.json',dict(results=results,training_samples=0,optimizer_steps=0))
        assert all(sha(path)==h for path,h in frozen.items())
        selection=select_difficulty(results)
        report=dict(passed=True,results=results,selection=selection,TRAIN_only=True,DEV_read=False,finaltest_touched=False,training_samples=0,optimizer_steps=0,
            expert_labels=0,independent_win_rate_claim=False,ability_improvement_claim=False)
    except BaseException as error:report=dict(passed=False,error=repr(error),completed_results=results,selection=select_difficulty([]),invalid_game_is_loss=False,training_samples=0,optimizer_steps=0)
    write(a.out/'RESULT.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('results','completed_results')},indent=2))
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
