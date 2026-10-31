"""Prespecified off/once same-binary diagnostic pairs; no optimizer or final test."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab');TRAIN=HERE.parent/'strategic-typed-training-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2))
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]
def schedule():
    jobs=[]
    for map_name in ['takeover-v2-train-01-mines','takeover-v2-train-02-development']:
        for opponent in ['EmptyAI','Nullkiller2']:
            for player in [0,1]:jobs.append(dict(map=map_name,opponent=opponent,player=player,seed=2026110900+len(jobs)))
    return jobs
def movements(path):
    result=[];last=0
    for line in path.read_text(errors='replace').splitlines():
        if 'DirectorTypedEvent ' in line:
            e=json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ',1)[1])[0]
            if e['event']=='native_action_sent' and e.get('decision_id') is not None:last=e['decision_id']
        m=re.search(r': Hero (.*?) starts movement from \(([-\d ]+)\) to \(([-\d ]+)\)\.',line)
        if m:result.append((m.groups(),last))
    return result
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    model=TRAIN/'cuda-curriculum-ack-01/update-1.pt';capsule=LAB/'evaluations/typed-bounded-replan-capsule-01'
    qualification=json.loads((LAB/'evaluations/typed-bounded-replan-qualification-01/RESULT.json').read_text());assert qualification['passed']
    sources=[Path(__file__),HERE/'run_game.py',HERE/'audit_replan.py',HERE/'PLAN.md',model,capsule/'EXECUTION.json']
    frozen={str(p):sha(p) for p in sources}
    write(a.out/'PLAN.json',dict(jobs=schedule(),modes={'a':'off','b':'once'},input_sha256=frozen,optimizer_steps=0,training_samples=0,
        meaning='Availability/observation diagnostic with unchanged5398 policy, not new learning or final test. All eight pairs retained.'))
    pairs=[]
    try:
        for i,job in enumerate(schedule()):
            pair=dict(pair=i,job=job,arms={})
            for arm,mode in [('a','off'),('b','once')]:
                assert all(sha(Path(p))==h for p,h in frozen.items());root=a.out/f'pair-{i:02d}'/arm;root.mkdir(parents=True)
                commands=[['/usr/bin/python3',HERE/'run_game.py','--capsule',capsule,'--checkpoint',model,'--map',job['map'],
                    '--seed',job['seed'],'--player',job['player'],'--opponent',job['opponent'],'--threat-replan',mode,'--out',root/'native'],
                    [LAB/'venv/bin/python',HERE.parent/'strategic-typed-native-v1/audit_game_v5.py',root/'native',root/'raw-audit'],
                    ['/usr/bin/python3',HERE/'audit_replan.py',root/'native',root/'raw-audit/AUDIT.json',root/'replan-audit']]
                for k,cmd in enumerate(commands):
                    r=subprocess.run(list(map(str,cmd)),capture_output=True,text=True);(root/f'command-{k}.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr)
                    assert r.returncode==0,'Invalid diagnostic arm; unscored and abort: '+str(root)
                proof=json.loads((root/'raw-audit/AUDIT.json').read_text());assert proof['whole_game_valid'] and proof['transport_drained']
                replan=json.loads((root/'replan-audit/AUDIT.json').read_text());assert replan['passed']
                terminal=next(x for x in rows(root/'native/strategy-trace.jsonl') if x['event'] in ('victory','defeat'))
                pair['arms'][arm]=dict(mode=mode,win=proof['winner']==('red' if job['player']==0 else 'blue'),winner=proof['winner'],
                    counts=proof['counts'],day=terminal['day'],releases=replan['releases'],changed_goal=replan['changed_goal'],changed_next=replan['changed_next'],
                    multiple_immediate_next_releases=replan['multiple_immediate_next_releases'])
            roots=[a.out/f'pair-{i:02d}/{arm}/native' for arm in ('a','b')]
            proposals=[rows(r/'agent/typed-broker.jsonl') for r in roots]
            rd=next((j+1 for j,(x,y) in enumerate(zip(*proposals)) if x['request']!=y['request']),None)
            ma,mb=[movements(r/'client.log') for r in roots]
            md=next((j for j,(x,y) in enumerate(zip(ma,mb)) if x[0]!=y[0]),None)
            replan=json.loads((a.out/f'pair-{i:02d}/b/replan-audit/AUDIT.json').read_text())
            first=min((x['decision_id'] for x in replan['details']),default=None)
            pair.update(win_delta=int(pair['arms']['b']['win'])-int(pair['arms']['a']['win']),first_request_difference=rd,first_release=first,
                initial_request_exact=proposals[0][0]['request']==proposals[1][0]['request'],
                first_movement_difference=None if md is None else md+1,
                observed_request_difference_before_release=rd is not None and (first is None or rd<first),
                movement_order_difference_before_release=md is not None and (first is None or max(ma[md][1],mb[md][1])<first))
            pairs.append(pair);write(a.out/'PROGRESS.json',dict(pairs=pairs,optimizer_steps=0));print(json.dumps(pair),flush=True)
        report=dict(passed=True,pairs=pairs,off_wins=sum(x['arms']['a']['win'] for x in pairs),once_wins=sum(x['arms']['b']['win'] for x in pairs),
            net_wins=sum(x['win_delta'] for x in pairs),releases=sum(x['arms']['b']['releases'] for x in pairs),
            changed_goal=sum(x['arms']['b']['changed_goal'] for x in pairs),changed_next=sum(x['arms']['b']['changed_next'] for x in pairs),
            optimizer_steps=0,training_samples=0,finaltest_touched=False,ability_improvement_claim=False,
            limitation='Eight training-map diagnostic pairs only. Same binary/seed does not certify hidden NPC history; inspect recorded pre-intervention differences. No safety/retreat or default-promotion certification.')
    except BaseException as error:report=dict(passed=False,error=repr(error),completed_pairs=pairs,optimizer_steps=0,training_samples=0)
    write(a.out/'RESULT.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('pairs','completed_pairs')},indent=2))
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
