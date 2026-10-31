"""Resume the frozen learner, not a new Adam or a new policy-source epoch.

The outer controller has its own frozen plan; the original collector, admission
and optimizer protocol sources stay byte-identical to saved update1.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent
sys.path.insert(0,str(RUN))
from pipeline_common import BASE,LAB,DEFAULT_CAPSULE,MAPS,source_inputs,capsule_inputs,validate_cells,sha
PARENT=LAB/'evaluations/strategic-learned-build-exploration-train-01/update-01/update-1.pt'
PARENT_SHA='d27d282bbcdaf1f1bf47f13b4b44c40ee1cd82639bedd47db90da5fd6c0da1d2'
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    assert sha(PARENT)==PARENT_SHA
    a.out.mkdir(parents=True,exist_ok=False)
    inputs=source_inputs()+capsule_inputs(DEFAULT_CAPSULE)+[Path(__file__).resolve(),HERE/'PLAN.md',PARENT]
    frozen={str(x):sha(x) for x in inputs}
    jobs=[]
    cells=[(m,o,player) for m in MAPS for o in ('EmptyAI','Nullkiller2') for player in (0,1)]
    for logical in (1,2,3):
        jobs.append(dict(logical_update=logical,target_update=logical+1,seed_base=2026103000+(logical-1)*100,
            cells=[dict(map=m,opponent=o,player=player,seed=2026103000+(logical-1)*100+i) for i,(m,o,player) in enumerate(cells)]))
    write(a.out/'PLAN.json',dict(execute=a.execute,parent=str(PARENT),parent_sha256=PARENT_SHA,updates=jobs,
        optimizer_reset=False,learner_global_seed=2026102800,original_source_protocol_unchanged=True,input_sha256=frozen,
        controller_scope='External schedule; not falsely added to existing checkpoint protocol. Every actual collection and trainer enforces its frozen original source/runtime protocol.',
        finaltest_touched=False,expert_labels_used=False))
    if not a.execute:print(json.dumps(dict(plan_only=True,new_games=24,new_updates=3,optimizer_steps=0)));return 0
    parent=PARENT;completed=[]
    try:
        for epoch in jobs:
            root=a.out/f'round-{epoch["target_update"]:02d}';root.mkdir();admissions=[];episodes=[]
            for i,job in enumerate(epoch['cells']):
                assert all(sha(Path(x))==h for x,h in frozen.items())
                cell=root/f'cell-{i:02d}';cell.mkdir();native=cell/'native';audit=cell/'raw-audit';admit=cell/'admitted';admissions.append(admit)
                collect=['/usr/bin/python3',str(RUN/'collect_episode_v5.py'),'--capsule',str(DEFAULT_CAPSULE),'--checkpoint',str(parent),
                    '--map',job['map'],'--opponent',job['opponent'],'--player',str(job['player']),'--seed',str(job['seed']),
                    '--logical-update',str(epoch['logical_update']),'--seconds','120','--out',str(native)]
                commands=[collect,[str(LAB/'venv/bin/python'),str(RUN/'audit_game_v6.py'),str(native),str(audit)],
                    [str(LAB/'gpu-venv/bin/python'),str(BASE/'admit_episode_v5.py'),'--run',str(native),'--native-audit',str(audit/'AUDIT.json'),'--out',str(admit)]]
                for stage,command in zip(('collect','audit','admit'),commands):
                    r=subprocess.run(command,capture_output=True,text=True);(cell/(stage+'.log')).write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
                    assert r.returncode==0,f'Update{epoch["target_update"]} cell{i} {stage} invalid; no partial update or retry'
                episodes.append(json.loads((admit/'episode.json').read_text()))
            validate_cells(episodes)
            out=root/'update';command=[str(LAB/'gpu-venv/bin/python'),str(BASE/'train_update_v3.py'),'--resume',str(parent),
                '--capsule',str(DEFAULT_CAPSULE),'--purpose','curriculum_training','--seed','2026102800','--out',str(out)]
            for d in admissions:command+=['--admission',str(d)]
            r=subprocess.run(command,capture_output=True,text=True);(root/'train.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
            assert r.returncode==0,'Full-state resume/update failed; preserve original report/checkpoint'
            result=json.loads((out/'RESULT.json').read_text())
            assert result['completed_update'] and result['training_updates']==epoch['target_update'] and result['cuda_optimizer_steps']>0
            assert sha(Path(result['checkpoint']))==result['checkpoint_sha256']
            parent=Path(result['checkpoint']);completed.append(result);write(a.out/'PROGRESS.json',dict(completed=completed))
        assert all(sha(Path(x))==h for x,h in frozen.items())
        result=dict(passed=True,completed=completed,checkpoint=str(parent),checkpoint_sha256=sha(parent),
            optimizer_reset=False,training_updates=4,ability_improvement_claim=False)
    except BaseException as error:
        result=dict(passed=False,error=repr(error),completed=completed,last_completed_checkpoint=str(parent),ability_improvement_claim=False)
    write(a.out/'RESULT.json',result);print(json.dumps({k:v for k,v in result.items() if k!='completed'},indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
