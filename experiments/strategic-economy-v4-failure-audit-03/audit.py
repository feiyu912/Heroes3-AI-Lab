"""Read-only timeout diagnosis after all four economy engineering games pass."""
import collections
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
V2=HERE.parent/'strategic-policy-v2';sys.path.insert(0,str(V2))
from audit_supply_raw import sha,records

run=HERE.parent/'strategic-economy-v4/acceptance-03'
execution=json.loads((run/'EXECUTION.json').read_text());assert execution['status']=='failed'
protocol=json.loads((run/'PROTOCOL.json').read_text());assert all(sha(p)==h for p,h in protocol['frozen'].items())
failed=run/execution['failed_episode'];smoke=json.loads((failed/'smoke-result.json').read_text())
native=smoke['native_result'];root=Path(native['run_dir']);agent=Path(smoke['agent_dir'])
trace=root/'strategy-trace.jsonl';log=root/'client.log';ds=root/'strategy-decisions.jsonl'
assert sha(trace)==native['strategy_trace_sha256']and sha(log)==native['log_sha256']
states=records(trace);counts=collections.Counter(s['event']for _,s in states)
assert counts['before_move']==counts['move_applied']==44 and not counts['move_failed']and not counts['economy_failed']
loglines=[re.sub(r'\x1b\[[0-9;]*m','',x)for x in log.read_text(errors='replace').splitlines()]
end=next(i for i in range(len(loglines)-1,-1,-1)if'Received CPack of type 11BattleEnded'in loglines[i])
context=[dict(line=i+1,text=loglines[i])for i in range(max(0,end-230),min(len(loglines),end+85))]
selected=[r for r in context if any(x in r['text']for x in('BattleEnded','PlayerBlocked','CHeroMovementQuery',
    'MapObjectVisitQuery','CBattleQuery','SetAvailableHero','removing object id=','MoveHero','QueryReply','PackageApplied'))]
commits=[r for _,r in records(agent/'broker-trace.jsonl')if r['event']=='decision_committed']
assert len(commits)==44
manifest=[]
for c in commits:
    request=agent/c['request_file'];action=agent/c['action_file']
    assert sha(request)==c['request_sha256']and sha(action)==c['response_sha256']
    manifest.append(dict(request=str(request),request_sha256=sha(request),action_sha256=sha(action)))
result=dict(schema='economy-v4-nk-battle-wakeup-timeout-v1',status='invalid_timeout_not_loss',
    native=native,smoke=smoke,validated_engineering=execution['episodes'],
    trace_event_counts=dict(counts),trace_tail=[dict(line=i,state=s)for i,s in states[-14:]],
    last_request=json.loads((agent/'request-00000044.json').read_text()),
    last_decision=records(ds)[-1],all44_request_response_hashes_verified=True,request_manifest=manifest,
    final_battle_log_context=context,final_battle_selected_context=selected,
    evidence={str(p):sha(p)for p in(trace,log,ds,failed/'smoke-result.json')},
    execution_sha256=sha(run/'EXECUTION.json'),input_freeze_verified=True,
    nk_valid_games=0,nk_losses=0,training_updates=0,bc_eligible=0)
target=HERE/'AUDIT.json';assert not target.exists();target.write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps(dict(status=result['status'],timed_out=native['timed_out'],completed=native['completed'],
    trace_event_counts=dict(counts),native_dir=str(root),trace_tail=result['trace_tail'][-5:]),ensure_ascii=False))
print(json.dumps(selected,ensure_ascii=False))
