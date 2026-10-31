"""One original terminal-race seed, strict native ACK gate and honest prefix diff."""
import json
from pathlib import Path
import re
import subprocess
import sys
import traceback

HERE=Path(__file__).resolve().parent
V2=HERE.parent/'strategic-policy-v2'
sys.path.insert(0,str(V2))
from run_supply_pilot import frozen_inputs,verify,atomic,terminate_owned,CHECKPOINT
from audit_supply_raw import sha,records,audit_episode


def main():
    out=HERE/'run-01';assert not out.exists();out.mkdir()
    frozen=frozen_inputs(CHECKPOINT)
    frozen[str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
    atomic(out/'PROTOCOL.json',dict(schema='query-ack-barrier-regression-v1',frozen=frozen,
        map='Maps/adv/takeover-v2-train-02-development',red='DirectorAI',blue='EmptyAI',seed=2026101860,
        checkpoint=str(CHECKPOINT),mode='legacy-policy',engineering_only=True))
    proc=None
    try:
        cmd=[sys.executable,str(V2/'smoke_game.py'),'--map','Maps/adv/takeover-v2-train-02-development',
            '--red','DirectorAI','--blue','EmptyAI','--seed','2026101860','--mode','legacy-policy',
            '--checkpoint',str(CHECKPOINT),'--seconds','120','--tag','query-ack-barrier-regression-01']
        with (out/'smoke.log').open('w')as log:
            proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);code=proc.wait()
        text=(out/'smoke.log').read_text(errors='replace');match=re.search(r'^AGENT_DIR=(.+)$',text,re.M)
        if match:
            source=Path(match[1].strip())/'smoke-result.json'
            if source.exists():(out/'smoke-result.json').write_bytes(source.read_bytes())
        assert code==0,'Native/protocol regression failed'
        verify(frozen)
        summary=json.loads((out/'smoke-result.json').read_text());root=Path(summary['native_result']['run_dir']);agent=Path(summary['agent_dir'])
        oldpath=HERE.parent/'strategic-economy-v4/acceptance-02/engineering-map1-red-2026101860/smoke-result.json'
        old=json.loads(oldpath.read_text());oldagent=Path(old['agent_dir'])
        prefix=[]
        for i in range(1,286):
            request=f'request-{i:08d}.json';action=f'action-{i:08d}.json'
            prefix.append(dict(request_id=i,request_bytes_identical=(agent/request).read_bytes()==(oldagent/request).read_bytes(),
                action_bytes_identical=(agent/action).read_bytes()==(oldagent/action).read_bytes(),
                old_request_sha256=sha(oldagent/request),new_request_sha256=sha(agent/request)))
        states=records(root/'strategy-trace.jsonl');pending=None;acks=[];terminal=None;terminal_actions=[]
        for line,s in states:
            event=s['event']
            if terminal and event.startswith('before_'):terminal_actions.append(dict(line=line,state=s))
            if event=='before_move':assert pending is None;pending=dict(line=line,state=s)
            elif event=='move_applied':
                assert pending is not None;acks.append(dict(before=pending,ack=dict(line=line,state=s)));pending=None
            elif event in ('move_failed','economy_failed'):raise AssertionError(dict(line=line,state=s))
            elif event in ('victory','defeat'):terminal=dict(line=line,state=s)
        log=[re.sub(r'\x1b\[[0-9;]*m','',x)for x in(root/'client.log').read_text(errors='replace').splitlines()]
        rejected=[dict(line=i,text=x)for i,x in enumerate(log,1)if any(t in x for t in(
            'has to answer queries before attempting any further actions','Player is not allowed to perform this action!',
            'Got false in applying'))or('10QueryReply'in x and any(t in x.lower()for t in('failed','failure','unsuccess','error')))]
        sent=sum('Sending a request "10QueryReply"'in x for x in log)
        succeeded=sum('Message 10QueryReply successfully applied!'in x for x in log)
        status=dict(schema='query-ack-barrier-functional-regression-v1',passed=False,
            prefix_comparison=prefix,prefix_request_first_difference=next((r['request_id']for r in prefix if not r['request_bytes_identical']),None),
            prefix_action_first_difference=next((r['request_id']for r in prefix if not r['action_bytes_identical']),None),
            confirmed_movement_acks=len(acks),pending_final_move=pending,terminal=terminal,terminal_actions=terminal_actions,
            query_sent=sent,query_success=succeeded,server_rejected=rejected,final_ack=acks[-1]if acks else None,
            trace_tail=[dict(line=i,state=s)for i,s in states[-12:]],log_tail=[dict(line=i+1,text=x)for i,x in enumerate(log)if i>=len(log)-150],
            evidence={str(p):sha(p)for p in(root/'client.log',root/'strategy-trace.jsonl',root/'strategy-decisions.jsonl')},
            ability_improvement_proven=False,bc_eligible=0)
        atomic(out/'DIAGNOSTIC.json',status)
        assert pending is None and terminal and not terminal_actions,'Terminal action/ACK gate failed'
        assert sent==succeeded and not rejected,'Query/server-rejection gate failed'
        raw=audit_episode(out/'smoke-result.json');atomic(out/'RAW_AUDIT.json',raw)
        assert len(acks)==raw['decisions']
        status['passed']=True;atomic(out/'FUNCTIONAL_AUDIT.json',status)
        atomic(out/'STATUS.json',dict(status='passed',raw_audit=str(out/'RAW_AUDIT.json')))
        print(json.dumps(dict(status='passed',requests=raw['decisions'],acks=len(acks),query_sent=sent,
            first_prefix_request_difference=status['prefix_request_first_difference'],
            first_prefix_action_difference=status['prefix_action_first_difference'],native_dir=str(root))),flush=True)
    except BaseException:
        if proc is not None:terminate_owned(proc)
        atomic(out/'STATUS.json',dict(status='failed',error=traceback.format_exc()))
        raise


if __name__=='__main__':main()
