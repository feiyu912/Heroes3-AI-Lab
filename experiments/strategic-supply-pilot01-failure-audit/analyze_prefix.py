import collections
import json
from pathlib import Path
from inspect_failure import HERE,V2
from audit_supply_raw import sha,records
from supply_policy import _pressure,MIN_DISPATCH_UTILITY,MIN_REINFORCEMENT_RATIO

failure=json.loads((HERE/'FAILURE_AUDIT.json').read_text());groups={};opportunities=[]
for ep in failure['first10']:
    groups.setdefault((ep['map'],ep['role'],ep['seed']),{})[ep['mode']]=ep
    if ep['mode']!='supply-aware':continue
    raw=json.loads(Path(ep['audit']).read_text());agent=Path(raw['agent_dir'])
    commits=[c for _,c in records(agent/'broker-trace.jsonl')if c['event']=='decision_committed']
    for c in commits:
        r=json.loads((agent/c['request_file']).read_text())
        supplies=[(i,s)for i,s in enumerate(r['candidates'])if s['kind']==4]
        if not supplies or r['candidates'][c['baseline_index']]['kind']==4:continue
        towns={tuple(t['position']):t['army_value']for t in r['own_towns']}
        own=r['own_army_value'];current=_pressure(r['from'],r['visible_threats'],own)
        basepressure=_pressure(r['candidates'][c['baseline_index']]['next'],r['visible_threats'],own)
        for index,s in supplies:
            ratio=towns[tuple(s['position'])]/own;step=_pressure(s['next'],r['visible_threats'],own)
            utility=ratio/(.5+s['path_cost'])*(1+.5*min(current,1))+max(-.25,min(.25,basepressure-step))
            opportunities.append(dict(request=str(agent/c['request_file']),request_sha256=c['request_sha256'],
                day=r['day'],hero=r['hero'],candidates_count=len(r['candidates']),
                baseline_kind=r['candidates'][c['baseline_index']]['kind'],supply_index=index,
                reinforcement_ratio=ratio,path_cost=s['path_cost'],utility=utility,
                ratio_gate_passed=ratio>=MIN_REINFORCEMENT_RATIO,utility_gate_passed=utility>=MIN_DISPATCH_UTILITY,
                step_pressure=step,current_pressure=current,baseline_pressure=basepressure,
                reason=c['override_reason']))
pairs=[]
for key,g in groups.items():
    assert set(g)=={'legacy-policy','supply-aware'}
    b,c=g['legacy-policy'],g['supply-aware']
    pairs.append(dict(map=key[0],role=key[1],seed=key[2],trace_sha_equal=b['trace_sha256']==c['trace_sha256'],
        delta_wins=c['won']-b['won'],delta_main_delivery=c['delivered_to_main_count']-b['delivered_to_main_count'],
        baseline_main_loss_day=b['original_main_loss_day'],supply_main_loss_day=c['original_main_loss_day']))
result=dict(schema='stopped-supply-prefix-diagnostic-v1',valid_prefix_pairs=5,registered_pairs=8,
    full_protocol_completed=False,pairs=pairs,nonsupply_baseline_with_supply_choice=len(opportunities),
    below_ratio_gate=sum(not r['ratio_gate_passed']for r in opportunities),
    below_utility_gate=sum(not r['utility_gate_passed']for r in opportunities),opportunities=opportunities,
    bc_eligible=0,ability_improvement_proven=False)
out=HERE/'PREFIX_DIAGNOSTIC.json';assert not out.exists();out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items()if k!='opportunities'}))
