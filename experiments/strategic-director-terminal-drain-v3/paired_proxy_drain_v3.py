"""Separate model/coordinate-proxy pairs with once mode identical in both arms."""
import argparse,itertools,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"strategic-threat-replan-v2"))
from pathlib import Path
from paired_diagnostic import sha,write,rows,movements
HERE=Path(__file__).resolve().parent;REPLAN=HERE.parent/'strategic-threat-replan-v2';LAB=Path('/root/heroes3-ai-lab');TRAIN=HERE.parent/'strategic-typed-training-v1'
def first_difference(a,b,key=lambda x:x):
    missing=object()
    return next((i for i,(x,y) in enumerate(itertools.zip_longest(a,b,fillvalue=missing)) if x is missing or y is missing or key(x)!=key(y)),None)
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    qualification=LAB/'evaluations/typed-director-terminal-drain-qualification-01'
    qualification_result=json.loads((qualification/'RESULT.json').read_text())
    qualification_plan=json.loads((qualification/'PLAN.json').read_text())
    assert qualification_result['passed'] and len(qualification_result['games'])==3
    assert qualification_plan['termination_registry_semantics']=='atomic-termination-closed-registry-v3'
    assert all(sha(Path(p))==h for p,h in qualification_plan['input_sha256'].items())
    assert all(g['registry']['termination_registry_semantics']=='atomic-termination-closed-registry-v3' and g['registry']['director_requests_cancelled']==0 for g in qualification_result['games'])
    binding_proof=HERE.parent/'strategic-request-bind-barrier-v2/native-repro-comparison-01/AUDIT.json'
    assert json.loads(binding_proof.read_text())['new_execution_certified']
    model=TRAIN/'cuda-curriculum-ack-01/update-1.pt';capsule=LAB/'evaluations/typed-director-terminal-drain-capsule-03'
    jobs=[]
    for map_name in ['takeover-v2-train-01-mines','takeover-v2-train-02-development']:
        for opponent in ['EmptyAI','Nullkiller2']:
            for player in [0,1]:jobs.append(dict(map=map_name,opponent=opponent,player=player,seed=2026111000+len(jobs)))
    sources=[Path(__file__),REPLAN/'paired_diagnostic.py',HERE/'run_proxy_game_director_drain.py',REPLAN/'clearance_broker.py',REPLAN/'clearance_proxy.py',
        HERE/'audit_replan_v3.py',REPLAN/'audit_proxy.py',REPLAN/'PROXY_PLAN.md',HERE.parent/'strategic-request-bind-barrier-v2/PLAN.md',model,capsule/'EXECUTION.json',capsule/'build-source-manifest.json',HERE/'PLAN.md',HERE/'CANDIDATE_MANIFEST.json',HERE/'director_registry_v1.py',HERE/'audit_game_v6.py']
    sources.extend([qualification/'RESULT.json',qualification/'PLAN.json',binding_proof])
    frozen={str(p):sha(p) for p in sources};write(a.out/'PLAN.json',dict(jobs=jobs,modes='once in both arms',arms={'a':'model','b':'clearance'},
        terminal_ack_scope='director',termination_registry_semantics='atomic-termination-closed-registry-v3',input_sha256=frozen,optimizer_steps=0,training_samples=0,expert_labels=0,finaltest_touched=False))
    pairs=[]
    try:
        for i,job in enumerate(jobs):
            pair=dict(pair=i,job=job,arms={})
            for arm,policy in [('a','model'),('b','clearance')]:
                assert all(sha(Path(p))==h for p,h in frozen.items());root=a.out/f'pair-{i:02d}'/arm;root.mkdir(parents=True)
                commands=[['/usr/bin/python3',HERE/'run_proxy_game_director_drain.py','--capsule',capsule,'--checkpoint',model,'--map',job['map'],
                    '--seed',job['seed'],'--player',job['player'],'--opponent',job['opponent'],'--threat-replan','once','--decision-policy',policy,'--out',root/'native'],
                    [LAB/'venv/bin/python',HERE/'audit_game_v6.py',root/'native',root/'raw-audit'],
                    [LAB/'venv/bin/python',HERE/'audit_replan_v3.py',root/'native',root/'raw-audit/AUDIT.json',root/'replan-audit'],
                    [LAB/'venv/bin/python',REPLAN/'audit_proxy.py',root/'native',root/'replan-audit/AUDIT.json',root/'proxy-audit']]
                for k,cmd in enumerate(commands):
                    r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);(root/f'command-{k}.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
                    assert r.returncode==0,'Invalid arm; unscored and abort: '+str(root)
                proof=json.loads((root/'raw-audit/AUDIT.json').read_text());proxy=json.loads((root/'proxy-audit/AUDIT.json').read_text())
                replan=json.loads((root/'replan-audit/AUDIT.json').read_text());assert proof['whole_game_valid'] and proxy['passed'] and replan['passed']
                terminal=next(x for x in rows(root/'native/strategy-trace.jsonl') if x['event'] in ('victory','defeat'))
                pair['arms'][arm]=dict(policy=policy,win=proof['winner']==('red' if job['player']==0 else 'blue'),winner=proof['winner'],day=terminal['day'],
                    counts=proof['counts'],releases=replan['releases'],overrides=proxy['overrides'])
            roots=[a.out/f'pair-{i:02d}/{arm}/native' for arm in ('a','b')];proposals=[rows(r/'agent/typed-broker.jsonl') for r in roots]
            rd=first_difference(*proposals,key=lambda x:x['request'])
            override=json.loads((a.out/f'pair-{i:02d}/b/proxy-audit/AUDIT.json').read_text());first=min((x['decision_id'] for x in override['details']),default=None)
            ma,mb=[movements(r/'client.log') for r in roots]
            before_b=[x for x in mb if first is None or x[1]<first]
            prefix_diff=first_difference(ma[:len(before_b)],before_b,key=lambda x:x[0])
            pair.update(win_delta=int(pair['arms']['b']['win'])-int(pair['arms']['a']['win']),first_override=first,
                first_request_difference=None if rd is None else rd+1,request_counts=list(map(len,proposals)),movement_counts=[len(ma),len(mb)],
                observed_request_difference_before_override=rd is not None and (first is None or rd+1<first),
                candidate_preoverride_movement_prefix_difference=None if prefix_diff is None else prefix_diff+1,
                limitation='Prefix difference can be ordering only; absence is not full hidden state equality. EOF differences retained.')
            pairs.append(pair);write(a.out/'PROGRESS.json',dict(pairs=pairs,optimizer_steps=0));print(json.dumps(pair),flush=True)
        result=dict(passed=True,pairs=pairs,model_wins=sum(x['arms']['a']['win'] for x in pairs),proxy_wins=sum(x['arms']['b']['win'] for x in pairs),
            net_wins=sum(x['win_delta'] for x in pairs),overrides=sum(x['arms']['b']['overrides'] for x in pairs),optimizer_steps=0,training_samples=0,
            expert_labels=0,finaltest_touched=False,ability_improvement_claim=False,meaning='Same preselected proxy cells rerun after failed transport batches, closed-registry atomic terminal epoch in BOTH arms. Not fresh independent, learned or expert evidence.')
    except BaseException as error:result=dict(passed=False,error=repr(error),completed_pairs=pairs,optimizer_steps=0,training_samples=0)
    write(a.out/'RESULT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('pairs','completed_pairs')},indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
