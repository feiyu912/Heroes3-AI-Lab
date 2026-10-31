"""One authorized native regression, then immutable prefix/ACK evidence."""
import collections
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
    frozen=frozen_inputs(CHECKPOINT);frozen[str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
    frozen[str(HERE.parent/'strategic-economy-v4/PLAN.md')]=sha(HERE.parent/'strategic-economy-v4/PLAN.md')
    atomic(out/'PROTOCOL.json',dict(schema='movement-barrier-regression-v1',frozen=frozen,
        map='Maps/adv/takeover-v2-train-01-mines',red='EmptyAI',blue='DirectorAI',seed=2026101860,
        checkpoint=str(CHECKPOINT),mode='legacy-policy',engineering_only=True))
    proc=None
    try:
        cmd=[sys.executable,str(V2/'smoke_game.py'),'--map','Maps/adv/takeover-v2-train-01-mines',
            '--red','EmptyAI','--blue','DirectorAI','--seed','2026101860','--mode','legacy-policy',
            '--checkpoint',str(CHECKPOINT),'--seconds','120','--tag','movement-barrier-regression-01']
        with (out/'smoke.log').open('w')as log:
            proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);code=proc.wait()
        text=(out/'smoke.log').read_text(errors='replace');match=re.search(r'^AGENT_DIR=(.+)$',text,re.M)
        if match:
            source=Path(match[1].strip())/'smoke-result.json'
            if source.exists():(out/'smoke-result.json').write_bytes(source.read_bytes())
        assert code==0,'Native/protocol regression failed'
        verify(frozen)
        summary=json.loads((out/'smoke-result.json').read_text());root=Path(summary['native_result']['run_dir']);agent=Path(summary['agent_dir'])
        states=records(root/'strategy-trace.jsonl');acks=[];pending=None;terminal=None;postterminal_actions=[]
        for line,state in states:
            event=state['event']
            if terminal and event.startswith('before_'):postterminal_actions.append(dict(line=line,state=state))
            if event=='before_move':
                assert pending is None,'A second move preceded previous ACK'
                pending=dict(line=line,state=state)
            elif event=='move_applied':
                assert pending is not None,'Unbound move ACK'
                acks.append(dict(before=pending,ack=dict(line=line,state=state)));pending=None
            elif event in ('move_failed','economy_failed'):
                raise AssertionError('Native failure state at line '+str(line))
            elif event in ('victory','defeat'):terminal=dict(line=line,state=state)
        assert pending is None,'Unconfirmed final movement request'
        assert terminal and not postterminal_actions,'No terminal or action issued after terminal'
        old=HERE.parent/'strategic-economy-v4/acceptance-01/engineering-map0-blue-2026101860/smoke-result.json'
        oldsummary=json.loads(old.read_text());oldagent=Path(oldsummary['agent_dir'])
        prefix=[]
        for i in range(1,296):
            request=f'request-{i:08d}.json';action=f'action-{i:08d}.json'
            assert (agent/request).read_bytes()==(oldagent/request).read_bytes(),f'Request prefix differs at {i}'
            assert (agent/action).read_bytes()==(oldagent/action).read_bytes(),f'Action prefix differs at {i}'
            prefix.append(dict(request_id=i,request_sha256=sha(agent/request),action_sha256=sha(agent/action)))
        log=[re.sub(r'\x1b\[[0-9;]*m','',x)for x in (root/'client.log').read_text(errors='replace').splitlines()]
        rejects=[dict(line=i,text=x)for i,x in enumerate(log,1)if'has to answer queries before attempting any further actions'in x
                 or ('10QueryReply'in x and any(v in x.lower()for v in ('failed','failure','unsuccess','error')))]
        qsent=sum('Sending a request "10QueryReply"'in x for x in log)
        qsuccess=sum('Message 10QueryReply successfully applied!'in x for x in log)
        assert qsent==qsuccess and not rejects,'Query ACK/rejection gate failed'
        counts=collections.Counter(s['event']for _,s in states)
        result=dict(schema='movement-barrier-regression-audit-v1',passed=True,
            prefix_requests_actions_identical=295,prefix=prefix,successful_move_acks=len(acks),
            final_movement_confirmed=True,no_postterminal_actions=True,terminal=terminal,
            tail_events=[dict(line=i,state=s)for i,s in states[-8:]],target_ack295=acks[294],
            native_movement_blocked=counts['native_movement_blocked'],native_movement_unblocked=counts['native_movement_unblocked'],
            query_sent=qsent,query_success=qsuccess,query_rejections=rejects,move_failures=0,economy_failures=0,
            evidence={str(p):sha(p)for p in (root/'client.log',root/'strategy-trace.jsonl',root/'strategy-decisions.jsonl',out/'smoke-result.json')},
            frozen=frozen,ability_improvement_proven=False,bc_eligible=0)
        atomic(out/'MOVEMENT_AUDIT.json',result)
        raw=audit_episode(out/'smoke-result.json');atomic(out/'RAW_AUDIT.json',raw)
        atomic(out/'STATUS.json',dict(status='passed',movement_audit=str(out/'MOVEMENT_AUDIT.json'),raw_audit=str(out/'RAW_AUDIT.json')))
        print(json.dumps(dict(status='passed',decisions=raw['decisions'],move_acks=len(acks),query_replies=qsent,
            prefix_identical=295,won=raw['won'],native_dir=str(root))),flush=True)
        return 0
    except BaseException:
        if proc is not None:terminate_owned(proc)
        atomic(out/'STATUS.json',dict(status='failed',error=traceback.format_exc()))
        raise


if __name__=='__main__':raise SystemExit(main())
