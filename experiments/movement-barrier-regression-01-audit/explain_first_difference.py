"""Explain the first state divergence using native post-battle ordering."""
import json
from pathlib import Path
import re
from run_and_compare import HERE,V2
from audit_supply_raw import sha

out=HERE/'run-01'
new=json.loads((out/'smoke-result.json').read_text())
oldpath=HERE.parent/'strategic-economy-v4/acceptance-01/engineering-map0-blue-2026101860/smoke-result.json'
old=json.loads(oldpath.read_text());result={}
for label,s in [('old',old),('new',new)]:
    root=Path(s['native_result']['run_dir']);agent=Path(s['agent_dir'])
    log=[re.sub(r'\x1b\[[0-9;]*m','',x)for x in (root/'client.log').read_text(errors='replace').splitlines()]
    steps=[i for i,x in enumerate(log)if'DirectorAI: step hero 'in x]
    step=steps[272]
    selected=[dict(line=i+1,text=log[i])for i in range(max(0,step-150),min(len(log),step+120))
        if any(t in log[i]for t in('BattleEnded','RemoveObject','removing object id=160;','step hero','PlayerBlocked','finishes visit','MapObjectVisitQuery','CHeroMovementQuery','CPathfinder'))]
    r272=json.loads((agent/'request-00000272.json').read_text());r273=json.loads((agent/'request-00000273.json').read_text())
    a272=int((agent/'action-00000272.json').read_text());a273=int((agent/'action-00000273.json').read_text())
    result[label]=dict(native_dir=str(root),log_sha256=sha(root/'client.log'),request272=r272,
        selected272=r272['candidates'][a272],request273=r273,selected273=r273['candidates'][a273],
        action272=a272,action273=a273,context=selected,
        checkpoint_sha256=json.loads((agent/'smoke-plan.json').read_text())['checkpoint_sha256'],
        broker_code=json.loads((agent/'smoke-plan.json').read_text())['code_sha256'],
        faction_config_sha256=sha(root/'config/factions/castle.json'),
        map_sha256=sha(root/'data/vcmi/Maps/adv/takeover-v2-train-01-mines.vmap'))
assert result['old']['checkpoint_sha256']==result['new']['checkpoint_sha256']
assert result['old']['broker_code']==result['new']['broker_code']
assert result['old']['faction_config_sha256']==result['new']['faction_config_sha256']
assert result['old']['map_sha256']==result['new']['map_sha256']
oldctx=result['old']['context'];newctx=result['new']['context']
oldstep=next(r['line']for r in oldctx if'DirectorAI: step hero'in r['text'])
oldremove=[r['line']for r in oldctx if'removing object id=160;'in r['text']]
newstep=next(r['line']for r in newctx if'DirectorAI: step hero'in r['text'])
newremove=[r['line']for r in newctx if'removing object id=160;'in r['text']]
assert oldremove and newremove
result.update(schema='movement-barrier-first-difference-cause-v1',
    unchanged_checkpoint_broker_map_faction=True,old_decision273_log_line=oldstep,new_decision273_log_line=newstep,
    old_guard_removal_log_lines=oldremove,new_guard_removal_log_lines=newremove,
    old_decision_precedes_client_guard_removal=oldstep<max(oldremove),
    new_decision_follows_client_guard_removal=newstep>max(newremove),
    causal_interpretation='The barrier delays reconsideration until the defeated guard object is removed and its visit/movement query is unblocked. Old request273 still committed to the stale neutral target; new request273 correctly lacks that defeated target. This is a legal earlier observable divergence, not an exact 295-action counterfactual.')
assert result['old_decision_precedes_client_guard_removal']and result['new_decision_follows_client_guard_removal']
target=out/'FIRST_DIFFERENCE_CAUSE.json';assert not target.exists();target.write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps({k:v for k,v in result.items()if k not in('old','new')},ensure_ascii=False))
for label in ('old','new'):print(label,json.dumps(result[label]['context']))
