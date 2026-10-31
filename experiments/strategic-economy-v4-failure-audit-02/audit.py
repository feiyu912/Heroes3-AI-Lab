"""Preserve the unconfirmed final movement detected by strict acceptance-02."""
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
V2=HERE.parent/'strategic-policy-v2';sys.path.insert(0,str(V2))
from audit_supply_raw import sha,records

run=HERE.parent/'strategic-economy-v4/acceptance-02'
execution=json.loads((run/'EXECUTION.json').read_text());assert execution['status']=='failed'
protocol=json.loads((run/'PROTOCOL.json').read_text());assert all(sha(p)==h for p,h in protocol['frozen'].items())
failed=run/execution['failed_episode'];smoke=json.loads((failed/'smoke-result.json').read_text())
native=smoke['native_result'];root=Path(native['run_dir']);agent=Path(smoke['agent_dir'])
trace=root/'strategy-trace.jsonl';log=root/'client.log';dec=root/'strategy-decisions.jsonl'
assert sha(trace)==native['strategy_trace_sha256']and sha(log)==native['log_sha256']
states=records(trace);pending=None;acks=[];afterterminal=[];terminal=None
for line,s in states:
    if terminal and s['event'].startswith('before_'):afterterminal.append(dict(line=line,state=s))
    if s['event']=='before_move':assert pending is None;pending=dict(line=line,state=s)
    elif s['event']=='move_applied':assert pending is not None;acks.append(dict(before=pending,after=dict(line=line,state=s)));pending=None
    elif s['event']in('victory','defeat'):terminal=dict(line=line,state=s)
rejected=[dict(line=i,state=s)for i,s in states if s['event']in('move_failed','economy_failed')]
assert pending is not None and not rejected and not afterterminal
ds=records(dec);number=len(ds);request=agent/f'request-{number:08d}.json'
loglines=[re.sub(r'\x1b\[[0-9;]*m','',x)for x in log.read_text(errors='replace').splitlines()]
step=[i for i,x in enumerate(loglines)if'DirectorAI: step hero 'in x][-1]
tail=[dict(line=i+1,text=loglines[i])for i in range(max(0,step-25),len(loglines))]
queries=[dict(line=i+1,text=x)for i,x in enumerate(loglines)if'has to answer queries before attempting any further actions'in x]
result=dict(schema='economy-v4-unconfirmed-final-action-audit-v1',status='strict_gate_failed',
    native_completed=native['completed'],smoke_io_passed=smoke['passed'],native_winner=native['winner'],
    issued_moves=number,successful_ack_states=len(acks),pending_final_move=pending,last_decision=ds[-1],
    last_request=json.loads(request.read_text()),last_request_sha256=sha(request),terminal=terminal,
    no_postterminal_actions=not afterterminal,trace_failures=rejected,query_rejections=queries,
    trace_tail=[dict(line=i,state=s)for i,s in states[-14:]],last_action_log_context=tail,
    evidence={str(p):sha(p)for p in(trace,log,dec,failed/'smoke-result.json')},
    execution_sha256=sha(run/'EXECUTION.json'),validated_prefix=execution['episodes'],
    engineering_gate_complete=False,nk_games_started=0,bc_eligible=0)
target=HERE/'AUDIT.json';assert not target.exists();target.write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps({k:result[k]for k in('status','native_completed','native_winner','issued_moves','successful_ack_states',
    'pending_final_move','last_decision','terminal','no_postterminal_actions','trace_failures','query_rejections')},ensure_ascii=False))
print(json.dumps([r for r in tail if any(v in r['text']for v in('DirectorAI:','8MoveHero','GameOver','gameOver','PlayerBlocked','All players','Game has','SHUTDOWN'))],ensure_ascii=False))
