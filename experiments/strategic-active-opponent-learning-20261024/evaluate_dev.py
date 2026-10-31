"""All fixed 24 unboosted DEV games; no data admission or model choice."""
import argparse,json,sys
from pathlib import Path
from pipeline_common import HERE,BASE,LAB,DEFAULT_INITIAL,INITIAL_SHA,DEFAULT_CAPSULE,source_inputs,capsule_inputs,sha
from run import run_command,write
def main():
    p=argparse.ArgumentParser();p.add_argument('--control',type=Path,required=True);p.add_argument('--curriculum',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    sys.path.insert(0,str(BASE));from model_io import load_model
    models=dict(initial=DEFAULT_INITIAL,control=a.control,curriculum=a.curriculum)
    assert sha(DEFAULT_INITIAL)==INITIAL_SHA
    for arm in ('control','curriculum'):
        _,bundle,_=load_model(models[arm]);assert bundle['complete_update_boundary'] and bundle['training_updates']==1
        assert bundle['parent_checkpoint_sha256']==INITIAL_SHA and bundle['protocol']['training_treatment']==arm
        assert all(sha(path)==h for path,h in bundle['protocol']['sources'].items())
    jobs=[dict(map=m,opponent=o,player=p,seed=2026104600+i) for i,(m,o,p) in enumerate((m,o,p) for m in ('takeover-v2-dev-01-river','takeover-v2-dev-02-reserves') for o in ('EmptyAI','Nullkiller2') for p in (0,1))]
    paths=source_inputs()+capsule_inputs(DEFAULT_CAPSULE)+list(models.values())+[LAB/('data/vcmi/Maps/adv/'+j['map']+'.vmap') for j in jobs]
    frozen={str(path):sha(path) for path in paths};a.out.mkdir(parents=True,exist_ok=False)
    write(a.out/'PLAN.json',dict(jobs=jobs,models={arm:dict(path=str(path),sha256=sha(path)) for arm,path in models.items()},input_sha256=frozen,optimizer_steps=0,admitted_samples=0,final_test_touched=False))
    if not a.execute:return 0
    pairs=[]
    try:
        for i,job in enumerate(jobs):
            pair=dict(index=i,job=job,arms={})
            for arm,checkpoint in models.items():
                assert all(sha(path)==h for path,h in frozen.items());root=a.out/f'pair-{i:02d}'/arm;root.mkdir(parents=True)
                commands=[[str(LAB/'venv/bin/python'),str(HERE/'collect_cpu.py'),'--capsule',str(DEFAULT_CAPSULE),'--checkpoint',str(checkpoint),'--out',str(root/'native'),'--map',job['map'],'--player',str(job['player']),'--opponent',job['opponent'],'--seed',str(job['seed']),'--seconds','120'],
                    [str(LAB/'venv/bin/python'),str(HERE/'audit_game_v6.py'),str(root/'native'),str(root/'raw-audit')]]
                for stage,command in zip(('collect','audit'),commands):run_command(command,root/(stage+'.log'))
                audit=json.loads((root/'raw-audit/AUDIT.json').read_text());assert audit['whole_game_valid'] and audit['native_game_completed'] and audit['transport_drained']
                proposals=[json.loads(x) for x in (root/'native/agent/typed-broker.jsonl').read_text().splitlines()]
                pair['arms'][arm]=dict(win=audit['winner']==('red' if job['player']==0 else 'blue'),counts=audit['counts'],audit_sha256=sha(root/'raw-audit/AUDIT.json'),initial_request_sha256=sha(root/'native/agent/request-00000001.json'),recruited_amount=sum(x['request']['candidates'][x['response']['selected_index']]['amount'] for x in proposals if x['response']['op']=='recruit'))
            pair['initial_request_equal_all_three']=len({x['initial_request_sha256'] for x in pair['arms'].values()})==1
            pairs.append(pair);write(a.out/'PROGRESS.json',dict(pairs=pairs))
        result=dict(passed=True,pairs=pairs,arm_wins={arm:sum(x['arms'][arm]['win'] for x in pairs) for arm in models},optimizer_steps=0,admitted_samples=0,model_promoted=False,final_test_touched=False)
    except BaseException as error:result=dict(passed=False,error=repr(error),completed_pairs=pairs)
    write(a.out/'RESULT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('pairs','completed_pairs')}));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
