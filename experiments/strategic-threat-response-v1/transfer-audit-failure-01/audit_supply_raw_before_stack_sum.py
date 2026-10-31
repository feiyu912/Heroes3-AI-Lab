"""Independent raw audit: lawful decisions, native hero losses, conserved supply."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
from supply_policy import choose


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def records(path):
    return [(i,json.loads(row)) for i,row in enumerate(Path(path).read_text().splitlines(),1) if row.strip()]


def army(state):
    return collections.Counter({int(creature):int(count) for creature,count in state['army']})


def audit_terminal_tail(states):
    terminals=[(i,line,state) for i,(line,state) in enumerate(states)
               if state['event'] in ('victory','defeat')]
    assert len(terminals)==1,'Expected exactly one native terminal'
    index,line,terminal=terminals[0]
    payload={k:v for k,v in terminal.items() if k!='event'}
    tail=[]
    for tail_line,state in states[index+1:]:
        assert state['event']=='native_battle_ready','Non-transport event after terminal'
        assert {k:v for k,v in state.items() if k!='event'}==payload,'State changed after terminal'
        tail.append(dict(line=tail_line,event=state['event'],state_identical_to_terminal=True))
    return dict(terminal_line=line,terminal_event=terminal['event'],entries=tail,count=len(tail))


def audit_episode(summary_path):
    smoke=json.loads(Path(summary_path).read_text())
    assert smoke['passed'] and smoke['inputs_unchanged'] and smoke['io_hashes_verified']
    native=smoke['native_result'];root=Path(native['run_dir']);agent=Path(smoke['agent_dir'])
    assert native['completed'] and not any(native[k] for k in ('timed_out','crashed','interrupted'))
    assert native['inputs_unchanged'] and native['failed_move_replies']==0
    assert native['actual_ai']=={k:native['config'][k] for k in ('red','blue')}
    log=root/'client.log';trace=root/'strategy-trace.jsonl';decisions=root/'strategy-decisions.jsonl'
    assert sha(log)==native['log_sha256'] and sha(trace)==native['strategy_trace_sha256']
    assert sha(decisions)==native['strategy_decisions_sha256']
    plan=json.loads((root/'plan.json').read_text())
    assert all(sha(p)==h for p,h in plan['hashes'].items())
    states=records(trace);ds=records(decisions)
    terminal_tail_transport=audit_terminal_tail(states)
    assert not any(s['event'] in ('economy_failed','move_failed') for _,s in states)
    broker=records(agent/'broker-trace.jsonl')
    commits=[r for _,r in broker if r['event']=='decision_committed']
    assert not any(r['event']=='protocol_error' for _,r in broker)
    assert len(ds)==len(commits)==smoke['requests']
    first=next(s for _,s in states if s['event']=='turn_start')
    assert len(first['heroes'])==1,'Pilot requires one original main hero'
    main_id=first['heroes'][0]['id']
    text=log.read_text(errors='replace')
    removal=[dict(line=i,text=re.sub(r'\x1b\[[0-9;]*m','',line)) for i,line in enumerate(text.splitlines(),1)
             if re.search(r'removing object id='+str(main_id)+r';',line)]
    last_present=None;first_absent=None
    for line,s in states:
        if any(h['id']==main_id for h in s['heroes']):
            if first_absent is None:last_present=dict(line=line,day=s['day'],event=s['event'])
        elif last_present and first_absent is None:
            first_absent=dict(line=line,day=s['day'],event=s['event'])
    betrayal='背叛' in text and any(h['id']==main_id for h in states[-1][1]['heroes'])
    if betrayal:
        main_status='terminal_betrayal_not_combat_death';loss_day=states[-1][1]['day']
    elif first_absent:
        assert removal,'Hero absence lacks native removal evidence'
        main_status='native_removed';loss_day=first_absent['day']
    elif any(h['id']==main_id for h in states[-1][1]['heroes']):
        main_status='present_at_terminal';loss_day=None
    elif removal:
        main_status='terminal_removal_day_unknown';loss_day=None
    else:
        main_status='present_at_terminal';loss_day=None
    deliveries=[]
    for j,(line,s) in enumerate(states):
        if s['event']!='before_army_transfer':continue
        assert j+1<len(states)
        next_line,after=states[j+1]
        assert after['event']=='economy_applied','Missing immediate successful transfer ACK state'
        own_before={h['id']:army(h) for h in s['heroes']};own_after={h['id']:army(h) for h in after['heroes']}
        town_before={t['id']:army(t) for t in s['towns']};town_after={t['id']:army(t) for t in after['towns']}
        assert set(own_before)==set(own_after) and set(town_before)==set(town_after)
        hero_deltas={k:own_after[k]-own_before[k] for k in own_before if own_after[k]!=own_before[k]}
        town_deltas={k:town_before[k]-town_after[k] for k in town_before if town_after[k]!=town_before[k]}
        assert len(hero_deltas)==len(town_deltas)==1,'Ambiguous transfer state'
        hero_id,gain=next(iter(hero_deltas.items()));town_id,loss=next(iter(town_deltas.items()))
        assert gain and gain==loss,'Transfer failed creature conservation'
        assert own_after[hero_id]==own_before[hero_id]+gain
        assert town_before[town_id]==town_after[town_id]+loss
        deliveries.append(dict(before_line=line,after_line=next_line,day=s['day'],hero=hero_id,town=town_id,
            creatures=dict(gain),count=sum(gain.values()),to_original_main=hero_id==main_id))
    overrides=[];single=0;supply_available=0;request_manifest=[]
    for (line,d),commit in zip(ds,commits):
        request=agent/commit['request_file'];action=agent/commit['action_file']
        assert sha(request)==commit['request_sha256'] and sha(action)==commit['response_sha256']
        r=json.loads(request.read_text());index=int(action.read_text().strip())
        assert r['schema']=='strategy-candidates-v3' and 0<=index<len(r['candidates'])
        assert index==commit['action']==d['selected_candidate']
        assert r['candidates']==d['candidates'] and r['hero']==d['hero'] and r['from']==d['from']
        single+=len(r['candidates'])==1;supply_available+=any(c['kind']==4 for c in r['candidates'])
        if smoke['mode']=='supply-aware':
            expected,reason=choose(r,commit['baseline_index'])
            assert expected==index and reason==commit['override_reason']
            if index!=commit['baseline_index']:
                assert r['candidates'][index]['kind']==4
                overrides.append(dict(decision_line=line,request_id=r['request_id'],day=r['day'],hero=r['hero'],
                    baseline=commit['baseline_index'],selected=index,reason=reason,
                    from_pos=r['from'],candidate=r['candidates'][index],
                    visible_threats=r['visible_threats'],own_towns=r['own_towns']))
        request_manifest.append(dict(path=str(request),sha256=sha(request),action_sha256=sha(action)))
    totals=collections.Counter();main_totals=collections.Counter()
    for d in deliveries:
        totals.update(d['creatures'])
        if d['to_original_main']:main_totals.update(d['creatures'])
    side='red' if native['config']['red']=='DirectorAI' else 'blue'
    return dict(schema='supply-native-episode-audit-v2',passed=True,mode=smoke['mode'],config=native['config'],
        terminal_tail_transport=terminal_tail_transport,
        won=int(native['winner']==side),winner=native['winner'],normal=True,decisions=len(ds),
        original_main_id=main_id,original_main_status=main_status,original_main_loss_day=loss_day,
        original_main_last_present=last_present,original_main_first_absent=first_absent,
        original_main_removal_log=removal,deliveries=deliveries,
        delivered_by_creature=dict(totals),delivered_to_main_by_creature=dict(main_totals),
        delivered_count=sum(totals.values()),delivered_to_main_count=sum(main_totals.values()),
        single_candidate_decisions=single,supply_candidate_decisions=supply_available,
        overrides=overrides,override_count=len(overrides),request_manifest=request_manifest,
        native_dir=str(root),agent_dir=str(agent),native_days=native['native_calendar_last_day'],
        initial_state_sha256=hashlib.sha256(json.dumps(first,sort_keys=True).encode()).hexdigest(),
        evidence_sha256={str(p):sha(p) for p in (Path(summary_path),log,trace,decisions,agent/'broker-trace.jsonl')},
        bc_eligible=False,independent_capability_test=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--summary',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists()
    result=audit_episode(args.summary)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps({k:result[k] for k in ('passed','mode','won','original_main_loss_day','original_main_status','delivered_count','delivered_to_main_count','override_count')}))


if __name__=='__main__':main()
