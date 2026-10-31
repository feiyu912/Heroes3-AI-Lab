"""Inspect the stopped pilot without changing any registered input or outcome."""
import collections
import hashlib
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
V2=HERE.parent/'strategic-policy-v2'
sys.path.insert(0,str(V2))
from supply_policy import choose
from audit_supply_raw import sha,records


def main():
    run=V2/'supply-native-pilot-01'
    execution=json.loads((run/'EXECUTION.json').read_text())
    assert execution['status']=='failed'
    protocol=json.loads((run/'PROTOCOL.json').read_text())
    assert all(sha(p)==h for p,h in protocol['frozen'].items())
    failed=run/execution['failed_episode']
    smoke=json.loads((failed/'smoke-result.json').read_text());native=smoke['native_result']
    root=Path(native['run_dir']);trace=root/'strategy-trace.jsonl';log=root/'client.log'
    assert sha(trace)==native['strategy_trace_sha256'] and sha(log)==native['log_sha256']
    states=records(trace);failures=[]
    for j,(line,s) in enumerate(states):
        if s['event'] not in ('economy_failed','move_failed'):continue
        failures.append(dict(line=line,state=s,previous=states[max(0,j-1)],next=states[min(len(states)-1,j+1)]))
    text=log.read_text(errors='replace').splitlines();errors=[]
    for i,line in enumerate(text):
        if ('DirectorAI: economy request finished' in line and 'success=0' in line) or 'complain' in line.lower() or 'not enough' in line.lower():
            errors.append(dict(line=i+1,context=[dict(line=j+1,text=re.sub(r'\x1b\[[0-9;]*m','',text[j]))for j in range(max(0,i-8),min(len(text),i+4))]))
    reason_counts=collections.Counter();single=0;decisions=0;supply_opportunities=0
    first10=[]
    for ep in execution['episodes']:
        raw=json.loads(Path(ep['audit']).read_text());first10.append(dict(**ep,trace_sha256=raw['evidence_sha256'][str(Path(raw['native_dir'])/'strategy-trace.jsonl')]))
        if ep['mode']!='supply-aware':continue
        agent=Path(raw['agent_dir'])
        commits=[r for _,r in records(agent/'broker-trace.jsonl')if r['event']=='decision_committed']
        for c in commits:
            r=json.loads((agent/c['request_file']).read_text());actual,reason=choose(r,c['baseline_index'])
            assert actual==c['action'] and reason==c['override_reason']
            reason_counts[reason]+=1;decisions+=1;single+=len(r['candidates'])==1
            supply_opportunities+=any(x['kind']==4 for x in r['candidates'])
    result=dict(schema='stopped-supply-pilot-failure-audit-v1',registered_inputs_unchanged=True,
        execution_sha256=sha(run/'EXECUTION.json'),failure_episode=execution['failed_episode'],
        failed_native_complete=native['completed'],smoke_protocol_passed=smoke['passed'],
        failure_records=failures,log_failure_context=errors,
        failed_evidence={str(p):sha(p)for p in (trace,log,failed/'smoke-result.json')},
        valid_audited_episodes=len(first10),first10=first10,supply_method_audited_decisions=decisions,
        supply_method_single_candidate_decisions=single,supply_candidate_opportunities=supply_opportunities,
        reason_counts=dict(reason_counts),performance_claim=False,bc_eligible=0)
    output=HERE/'FAILURE_AUDIT.json';assert not output.exists();output.write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps({k:v for k,v in result.items()if k not in ('first10','log_failure_context')},ensure_ascii=False))


if __name__=='__main__':main()
