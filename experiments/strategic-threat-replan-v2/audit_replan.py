"""Read-only bind bounded replan events to actual published/consumed native decisions."""
import argparse,hashlib,json,re
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
def audit(root,native_audit,out):
    out.mkdir(parents=True,exist_ok=False)
    proof=json.loads(native_audit.read_text());assert proof['whole_game_valid'] and proof['native_game_completed'] and proof['transport_drained'] and not proof['contract_errors']
    plan=json.loads((root/'PLAN.json').read_text());mode=plan['threat_replan'];owned=plan['owned_player'];assert mode in ('off','once')
    raw=(root/'client.log').read_text(errors='replace')
    assert re.findall(r'DirectorThreatReplanMode player=(\d+) mode=(off|once)',raw)==[(str(owned),mode)]
    mirror=[];positions={};sent={}
    for number,line in enumerate(raw.splitlines(),1):
        if 'DirectorThreatReplan {' in line:
            e=json.JSONDecoder().raw_decode(line.split('DirectorThreatReplan ',1)[1])[0];mirror.append(e);positions[e['decision_id']]=number
        if 'DirectorTypedEvent ' in line:
            e=json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ',1)[1])[0]
            if e['event']=='native_action_sent' and e.get('decision_id') is not None:sent[e['decision_id']]=number
    sidecar=root/'strategy-trace.jsonl.replan.jsonl';releases=read(sidecar);assert releases==mirror
    if mode=='off':assert not releases
    proposals=read(root/'agent/typed-broker.jsonl');byid={p['request']['request_id']:p for p in proposals};assert len(byid)==len(proposals)
    budget=set();details=[]
    for e in releases:
        assert e['event']=='bounded_threat_replan' and e['player']==owned and type(e['decision_id']) is int
        p=byid[e['decision_id']];q=p['request'];c=q['candidates'];r=p['response'];key=(e['hero'],e['own_turn'])
        assert key not in budget;budget.add(key)
        assert (e['hero'],e['own_turn'],e['day'],e['from'])==(q['hero'],q['own_turn'],q['day'],q['from'])
        assert positions[e['decision_id']]<sent[e['decision_id']]
        moves=[x for x in c if x['op']=='move'];assert len(moves)==e['available_moves'] and len(moves)>1
        assert e['own_army_value']==q['own_army_value'] and e['own_army_value']>0 and e['threat'] in q['visible_threats']
        h,t=e['from'],e['threat']['position'];assert h[2]==t[2] and max(abs(h[0]-t[0]),abs(h[1]-t[1]))<=12
        assert e['threat']['approx_army_value']>=1.5*e['own_army_value']
        previous=[old for old in proposals if old['request']['request_id']<e['decision_id'] and (old['request']['hero'],old['request']['own_turn'])==key and old['response']['op']=='move']
        assert previous
        old=previous[-1];old_choice=old['request']['candidates'][old['response']['selected_index']]
        assert (old_choice['position'],old_choice['kind'])==(e['previous_goal'],e['previous_kind'])
        retained=[x for x in moves if (x['position'],x['kind'])==(e['previous_goal'],e['previous_kind'])];assert len(retained)==1
        choice=c[r['selected_index']]
        details.append(dict(decision_id=e['decision_id'],day=e['day'],hero=e['hero'],own_turn=e['own_turn'],request_sha256=r['request_sha256'],
            available_moves=len(moves),unique_next_tiles=len({tuple(x['next']) for x in moves}),selected_op=r['op'],
            changed_goal=r['op']=='move' and (choice['position'],choice['kind'])!=(e['previous_goal'],e['previous_kind']),
            changed_next=r['op']=='move' and choice['next']!=retained[0]['next']))
    inputs=[root/'PLAN.json',root/'client.log',root/'agent/typed-broker.jsonl',native_audit,Path(__file__)]+([sidecar] if sidecar.exists() else [])
    report=dict(passed=True,mode=mode,releases=len(releases),multiple_immediate_next_releases=sum(d['unique_next_tiles']>1 for d in details),
        changed_goal=sum(d['changed_goal'] for d in details),changed_next=sum(d['changed_next'] for d in details),details=details,
        input_sha256={str(p):sha(p) for p in inputs},optimizer_steps=0,training_samples=0,
        limitation='Actual bounded replanning opportunity/consumption, not safe retreat, expert behavior or causal win improvement.')
    (out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('details','input_sha256')},indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('native_audit',type=Path);p.add_argument('out',type=Path);a=p.parse_args();audit(a.root,a.native_audit,a.out)
