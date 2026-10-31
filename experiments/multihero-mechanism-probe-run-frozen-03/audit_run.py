#!/usr/bin/env python3
"""Strict read-only raw probe gate. Engineering result, never a game win/loss."""
from collections import Counter
import argparse,hashlib,json,re
from pathlib import Path
from capsule_support import thread_server_gate

def load_lines(path):return [json.loads(line) for line in path.read_text().splitlines()]
def army(state,hero):
    row=next(row for row in state['heroes'] if row['id']==hero)
    c=Counter()
    for creature,count in row['army']:
        assert isinstance(count,int) and count>0
        c[creature]+=count
    return c

def gate(events,trace,log,variant):
    def event(name):
        found=[(i,row) for i,row in enumerate(events) if row['event']==name]
        assert len(found)==1,f'Exactly one {name} required'
        return found[0]
    callback_i,callback=event('exchange_callback')
    assert callback['courier']!=callback['receiver'] and callback['query_id']>=0
    issued=[row for row in events if row['event']=='move_sent']
    assert issued and len({r['request_id'] for r in issued})==len(issued)
    applied=[row for row in events if row['event']=='move_ack']
    steps=re.findall(r'DirectorAI: step hero (\d+) (\([^\n]+?\)) -> (\([^\n]+?\)) reason=PURE_ENGINEERING_actual_owned_hero_meeting',log)
    assert len(steps)==len(issued) and all(start!=end for _,start,end in steps),'Real distinct-position MoveHero evidence required'
    assert all(int(hero)==callback['courier'] for hero,_,_ in steps)
    before=next(row for row in trace if row['event']=='probe_before_exchange')
    receiver_state=next(h for h in before['heroes'] if h['id']==callback['receiver'])
    final_target=tuple(int(n) for n in re.findall(r'-?\d+',steps[-1][2]))
    assert final_target==(receiver_state['x'],receiver_state['y'],receiver_state['z']),'Move must really target the other hero tile'
    assert 'visits ' in log,'Native object visit evidence required'
    assert not any(row['event'] in ('victory','defeat') for row in trace),'This probe must not claim a terminal game'
    if variant=='original-unhandled':
        assert not any(r['event'] in ('close_sent','transfer_sent','probe_completed_nonterminal') for r in events)
        rejection='has to answer queries' in log or 'Got false in applying' in log
        return {'engineering_pass':False,'negative_control_unhandled_callback_observed':True,
                'native_rejection_observed':rejection,'winner':None,'game_completed':False,
                'note':'A callback without reply is source-consistent negative evidence; no successful exchange is claimed.'}
    assert {r['request_id'] for r in issued}=={r['request_id'] for r in applied} and all(r['result']==1 for r in applied)
    assert len(applied)==len(issued),'Every native move must have its exact successful ACK'
    replies=re.findall(r'DirectorAI: step finished result=(\d+)',log)
    assert len(replies)==len(issued) and all(int(result)!=0 for result in replies)
    assert not any(row.get('failed') for row in events)
    assert not any(row['event'] in ('fixture_hero_count_invalid','fixture_target_invalid','fixture_no_real_path',
        'transfer_fixture_invalid','transfer_no_legal_slot') for row in events)
    close_i,close=event('close_sent');ack_i,ack=event('close_ack')
    assert callback_i<close_i<ack_i and close['request_id']==ack['request_id'] and ack['result']==1
    assert close['query_id']==callback['query_id']==ack['query_id']
    resolved_i,resolved=event('exchange_query_resolved');assert resolved_i>close_i and resolved['query_id']==callback['query_id']
    end_sent_i,end_sent=event('endturn_sent');end_i,end=event('endturn_ack');complete_i,complete=event('probe_completed_nonterminal')
    assert max(ack_i,resolved_i)<end_sent_i<end_i<complete_i and end['result']==1
    assert end['request_id']==end_sent['request_id'] and not complete['pending_move'] and complete['pending_queries']==0 and complete['query_requests']==0
    assert not any(row['event'] in ('move_sent','transfer_sent','close_sent') for row in events[complete_i+1:]),'No extra action after proved boundary'
    assert not any(token in log for token in ('has to answer queries','Got false in applying','external policy failed'))
    assert not any(row['event'] in ('move_failed','economy_failed','query_failed') for row in trace)
    after=next(row for row in trace if row['event']=='probe_after_close')
    donor=callback['courier'];receiver=callback['receiver']
    db,rb,da,ra=army(before,donor),army(before,receiver),army(after,donor),army(after,receiver)
    assert sum(da.values())>=1 and sum(ra.values())>=1 and db+rb==da+ra
    assert [(h['id'],h['x'],h['y'],h['z']) for h in before['heroes']]==[(h['id'],h['x'],h['y'],h['z']) for h in after['heroes']]
    assert (before['gold'],before['wood'],before['ore'])==(after['gold'],after['wood'],after['ore'])
    if variant=='transfer-close':
        sent_i,sent=event('transfer_sent');tack_i,tack=event('transfer_ack')
        assert callback_i<sent_i<tack_i<close_i and sent['request_id']==tack['request_id'] and tack['result']==1
        assert sent['query_id']==callback['query_id']==tack['query_id']
        assert db!=da and rb!=ra and (db-da)==(ra-rb) and bool(db-da)
    else:
        assert db==da and rb==ra and not any(r['event']=='transfer_sent' for r in events)
    return {'engineering_pass':True,'winner':None,'game_completed':False,'controlled_boundary':'successful native EndTurn ACK after query close',
        'transfer_confirmed':variant=='transfer-close','postcompletion_events_preserved':events[complete_i+1:],
        'training_samples':0,'optimizer_steps':0}

def audit(directory):
    plan=json.loads((directory/'plan.json').read_text());execution=json.loads((directory/'execution.json').read_text())
    assert plan['engineering_only'] and not plan['policy_broker']
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in plan['hashes'].items()),'Frozen input changed'
    assert execution['loaded_library_verified'] and not execution['loaded_library_errors'],'Actual client/server capsule loading not proven'
    assert plan['native_server_mode']=='thread' and plan['settings_server_useProcess'] is False
    events=load_lines(directory/'probe.jsonl');trace=load_lines(directory/'strategy-trace.jsonl')
    log=(directory/'client.log').read_text(errors='replace')
    settings=json.loads((directory/'config/settings.json').read_text())
    thread_proof=thread_server_gate(execution['loaded_library_observations'],log,settings['server']['useProcess'])
    assert thread_proof==execution['thread_server_verification'],'Recorded thread-server evidence differs from independent gate'
    result=gate(events,trace,log,plan['variant'])
    if result['engineering_pass']:assert execution['controlled_stop'] and not execution['timed_out']
    assert not list(directory.rglob('request-*.json')) and not list(directory.rglob('action-*.json'))
    result.update(execution=execution,raw_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (directory/'probe.jsonl',directory/'strategy-trace.jsonl',directory/'client.log')})
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args()
    try:report=audit(a.run)
    except Exception as e:report={'engineering_pass':False,'error':repr(e),'winner':None,'game_completed':False,'optimizer_steps':0}
    (a.run/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
