"""Read-only native regression audit of the exact failed seed/action prefix."""
import difflib
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'strategic-policy-v2/supply-native-pilot-01/map1-red-2026101852-legacy-policy/smoke-result.json'
NEW=Path('/root/heroes3-ai-lab/workers/strategy-agent-runs/query-drain-regression-01-ufw7_aib/smoke-result.json')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(path):return [json.loads(x)for x in Path(path).read_text().splitlines()]
def clean(line):return re.sub(r'\x1b\[[0-9;]*m','',line)


def main():
    old=json.loads(OLD.read_text());new=json.loads(NEW.read_text())
    assert new['passed'] and new['mode']==old['mode']=='legacy-policy'
    assert new['native_result']['config']['seed']==old['native_result']['config']['seed']==2026101852
    oa,na=Path(old['agent_dir']),Path(new['agent_dir'])
    on,nn=Path(old['native_result']['run_dir']),Path(new['native_result']['run_dir'])
    op=json.loads((oa/'smoke-plan.json').read_text());np=json.loads((na/'smoke-plan.json').read_text())
    assert op['checkpoint_sha256']==np['checkpoint_sha256']
    assert op['code_sha256']==np['code_sha256'],'Broker/model code changed in native-only regression'
    comparison=[]
    for i in range(1,157):
        name=f'request-{i:08d}.json';action=f'action-{i:08d}.json'
        ob,nb=(oa/name).read_bytes(),(na/name).read_bytes()
        same_request=json.loads(ob)==json.loads(nb)
        same_action=(oa/action).read_bytes()==(na/action).read_bytes()
        comparison.append(dict(request_id=i,request_equal=same_request,action_equal=same_action,
            old_request_sha256=sha(oa/name),new_request_sha256=sha(na/name),action_sha256=sha(na/action)))
    first_diff=next((r['request_id']for r in comparison if not r['request_equal']or not r['action_equal']),None)
    newstates=rows(nn/'strategy-trace.jsonl');oldstates=rows(on/'strategy-trace.jsonl')
    newds=rows(nn/'strategy-decisions.jsonl');oldds=rows(on/'strategy-decisions.jsonl')
    assert oldstates[384]['event']=='move_failed'
    assert all(s['event']not in ('move_failed','economy_failed')for s in newstates)
    target=newds[155]
    assert target==oldds[155],'Targeted failed action was not reproduced'
    before=[(i,s)for i,s in enumerate(newstates,1)if s['event']=='before_move'][155]
    follow=[dict(line=i,state=s)for i,s in list(enumerate(newstates,1))[before[0]-1:before[0]+4]]
    day18=[dict(line=i,state=s)for i,s in enumerate(newstates,1)if s['day']==18 and s['event']in ('turn_start','turn_end','move_applied','move_failed')]
    newlog=[clean(x)for x in (nn/'client.log').read_text(errors='replace').splitlines()]
    oldlog=[clean(x)for x in (on/'client.log').read_text(errors='replace').splitlines()]
    step_indices=[i for i,x in enumerate(newlog)if 'DirectorAI: step hero 'in x]
    step156=step_indices[155]
    contexts=[dict(line=i+1,text=newlog[i])for i in range(max(0,step156-100),min(len(newlog),step156+110))]
    def query_stats(log):
        sends=[dict(line=i+1,text=x)for i,x in enumerate(log)if 'Sending a request "10QueryReply"'in x]
        success=[dict(line=i+1,text=x)for i,x in enumerate(log)if 'Message 10QueryReply successfully applied!'in x]
        failure=[dict(line=i+1,text=x)for i,x in enumerate(log)if
            ('10QueryReply'in x and any(t in x.lower()for t in ('unsuccess','failed','failure','error')))
            or 'has to answer queries before attempting any further actions' in x]
        return dict(sends=len(sends),successfully_applied=len(success),failure_lines=failure,
                    sent_equal_success=len(sends)==len(success))
    stats=query_stats(newlog);oldstats=query_stats(oldlog)
    assert not stats['failure_lines']
    diff=list(difflib.unified_diff((on/'source-snapshot/CDirectorAI.cpp').read_text().splitlines(),
        (nn/'source-snapshot/CDirectorAI.cpp').read_text().splitlines(),fromfile='old-native-source',tofile='query-only-native-source'))
    result=dict(schema='query-drain-native-regression-readonly-v1',passed=first_diff is None and not stats['failure_lines'],
        raw_episode_audit_sha256=sha(HERE/'RAW_AUDIT.json'),checkpoint_sha256=np['checkpoint_sha256'],
        broker_model_sources_same=True,prefix_compared=156,prefix_first_difference=first_diff,
        prefix_requests_and_actions=comparison,target_decision156=target,new_trace_following_decision156=follow,
        day18_move_and_end_states=day18,new_target_log_context=contexts,
        new_query_stats=stats,old_query_stats=oldstats,full_new_move_failures=0,full_new_economy_failures=0,
        old_source_sha256=sha(on/'source-snapshot/CDirectorAI.cpp'),new_source_sha256=sha(nn/'source-snapshot/CDirectorAI.cpp'),
        source_diff=diff,old_native=old['native_result'],new_native=new['native_result'],
        old_log_sha256=sha(on/'client.log'),new_log_sha256=sha(nn/'client.log'),
        ability_improvement_proven=False,bc_eligible=False)
    out=HERE/'COMPARISON.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps({k:result[k]for k in ('passed','prefix_compared','prefix_first_difference','new_query_stats','old_query_stats','full_new_move_failures','full_new_economy_failures')}))
    print(json.dumps(follow))


if __name__=='__main__':main()
