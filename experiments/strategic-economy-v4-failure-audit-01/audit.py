"""Read-only diagnosis after the registered economy batch stopped."""
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
V2=HERE.parent/'strategic-policy-v2';sys.path.insert(0,str(V2))
from audit_supply_raw import sha,records


def main():
    run=HERE.parent/'strategic-economy-v4/acceptance-01'
    execution=json.loads((run/'EXECUTION.json').read_text());assert execution['status']=='failed'
    protocol=json.loads((run/'PROTOCOL.json').read_text())
    assert all(sha(p)==h for p,h in protocol['frozen'].items())
    failed=run/execution['failed_episode'];smoke=json.loads((failed/'smoke-result.json').read_text())
    native=smoke['native_result'];root=Path(native['run_dir']);agent=Path(smoke['agent_dir'])
    trace=root/'strategy-trace.jsonl';log=root/'client.log';ds=root/'strategy-decisions.jsonl'
    assert sha(trace)==native['strategy_trace_sha256']and sha(log)==native['log_sha256']
    states=records(trace);decisions=records(ds)
    loglines=[re.sub(r'\x1b\[[0-9;]*m','',x)for x in log.read_text(errors='replace').splitlines()]
    step_lines=[i for i,x in enumerate(loglines)if 'DirectorAI: step hero 'in x]
    failures=[]
    for j,(line,s)in enumerate(states):
        if s['event']not in ('move_failed','economy_failed'):continue
        item=dict(line=line,state=s,previous=states[j-1],next=states[j+1])
        if s['event']=='move_failed':
            number=sum(r['event']=='before_move'for _,r in states[:j])
            item['decision_number']=number;item['decision']=decisions[number-1]
            request=agent/f'request-{number:08d}.json'
            item['request']=json.loads(request.read_text());item['request_sha256']=sha(request)
            step=step_lines[number-1]
            item['log_context']=[dict(line=i+1,text=loglines[i])for i in range(max(0,step-60),min(len(loglines),step+140))]
        failures.append(item)
    rejections=[dict(line=i+1,text=x)for i,x in enumerate(loglines)if
        'has to answer queries before attempting any further actions'in x or 'Top Query:'in x
        or ('DirectorAI: economy request finished'in x and'success=0'in x)]
    result=dict(schema='economy-v4-stopped-native-failure-audit-v1',registered_inputs_unchanged=True,
        execution_sha256=sha(run/'EXECUTION.json'),failed_episode=execution['failed_episode'],
        smoke_passed=smoke['passed'],native_completed=native['completed'],failure_records=failures,
        rejection_lines=rejections,validated_prefix=execution['episodes'],
        evidence={str(p):sha(p)for p in (trace,log,ds,failed/'smoke-result.json')},
        engineering_gate_complete=False,nk_games_started=0,bc_eligible=0)
    out=HERE/'AUDIT.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps(dict(failed_episode=result['failed_episode'],failure_count=len(failures),
        failures=[dict(line=x['line'],event=x['state']['event'],day=x['state']['day'],
            previous_event=x['previous'][1]['event'],decision_number=x.get('decision_number'),
            hero=x['state']['heroes'])for x in failures],rejections=rejections),ensure_ascii=False))


if __name__=='__main__':main()
