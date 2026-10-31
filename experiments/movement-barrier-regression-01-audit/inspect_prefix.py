"""Diagnose, never erase, the failed exact-prefix comparison."""
import difflib
import json
from pathlib import Path
import re
import sys
from run_and_compare import HERE,V2
sys.path.insert(0,str(V2))
from audit_supply_raw import sha,records

out=HERE/'run-01'
new=json.loads((out/'smoke-result.json').read_text())
old=json.loads((HERE.parent/'strategic-economy-v4/acceptance-01/engineering-map0-blue-2026101860/smoke-result.json').read_text())
na,oa=Path(new['agent_dir']),Path(old['agent_dir']);nn,on=Path(new['native_result']['run_dir']),Path(old['native_result']['run_dir'])
differences=[];actions=[]
for i in range(1,296):
    request=f'request-{i:08d}.json';action=f'action-{i:08d}.json'
    n=json.loads((na/request).read_text());o=json.loads((oa/request).read_text())
    if n!=o:
        changed={k:dict(old=o.get(k),new=n.get(k))for k in set(n)|set(o)if n.get(k)!=o.get(k)}
        differences.append(dict(id=i,changed=changed,old_sha256=sha(oa/request),new_sha256=sha(na/request)))
    if(na/action).read_bytes()!=(oa/action).read_bytes():actions.append(dict(id=i,old=(oa/action).read_text(),new=(na/action).read_text()))
states=records(nn/'strategy-trace.jsonl');pending=None;acks=[];terminal=None
for line,s in states:
    if terminal:assert not s['event'].startswith('before_')
    if s['event']=='before_move':assert pending is None;pending=dict(line=line,state=s)
    elif s['event']=='move_applied':assert pending is not None;acks.append(dict(before=pending,after=dict(line=line,state=s)));pending=None
    elif s['event']in('move_failed','economy_failed'):raise AssertionError(s)
    elif s['event']in('victory','defeat'):terminal=dict(line=line,state=s)
assert pending is None and terminal
log=[re.sub(r'\x1b\[[0-9;]*m','',x)for x in(nn/'client.log').read_text(errors='replace').splitlines()]
sent=sum('Sending a request "10QueryReply"'in x for x in log);success=sum('Message 10QueryReply successfully applied!'in x for x in log)
rejected=[dict(line=i,text=x)for i,x in enumerate(log,1)if'has to answer queries before attempting any further actions'in x
    or('10QueryReply'in x and any(v in x.lower()for v in('failed','failure','error','unsuccess')))]
first_diff=differences[0]['id']if differences else None
contexts=[]
if first_diff:
    step=[i for i,x in enumerate(log)if'DirectorAI: step hero 'in x][first_diff-1]
    contexts=[dict(line=i+1,text=log[i])for i in range(max(0,step-130),min(len(log),step+65))]
result=dict(schema='movement-barrier-prefix-mismatch-readonly-v1',original_prefix_gate_status='failed',
    prefix_request_first_difference=first_diff,prefix_action_first_difference=actions[0]['id']if actions else None,
    request_differences=differences,action_differences=actions,
    all_move_requests_confirmed=True,successful_acks=len(acks),final_ack=acks[-1],
    target_old295_new295_ack=acks[294]if len(acks)>=295 else None,terminal=terminal,
    query_sent=sent,query_success=success,query_rejections=rejected,
    new_log_first_difference_context=contexts,
    native_source_diff=list(difflib.unified_diff((on/'source-snapshot/CDirectorAI.cpp').read_text().splitlines(),
        (nn/'source-snapshot/CDirectorAI.cpp').read_text().splitlines())),
    evidence={str(p):sha(p)for p in(nn/'client.log',nn/'strategy-trace.jsonl',nn/'strategy-decisions.jsonl')})
target=out/'PREFIX_DIAGNOSIS.json';assert not target.exists();target.write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps(dict(first_request_difference=first_diff,request_difference_count=len(differences),action_difference_count=len(actions),
    first_action_difference=result['prefix_action_first_difference'],acks=len(acks),query_sent=sent,query_success=success,query_rejections=rejected,
    first_diff_changes=differences[0]if differences else None),ensure_ascii=False))
