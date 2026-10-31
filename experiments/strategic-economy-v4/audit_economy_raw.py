"""Native scripted-economy acceptance from actual successful state changes."""
import collections
import json
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'strategic-policy-v2'))
from audit_supply_raw import audit_episode,records,army,sha


def total_own(state):
    result=collections.Counter()
    for unit in state['heroes']+state['towns']:
        result.update(army(unit))
    return result


def audit_economy(summary):
    raw=audit_episode(summary)
    native=Path(raw['native_dir']);states=records(native/'strategy-trace.jsonl')
    # Acceptance-02 strengthens the explicit final-action check; acceptance-01's
    # original auditor is preserved in its registered source snapshot.
    pending_move=None
    confirmed_moves=[]
    terminal_seen=False
    for line,state in states:
        event=state['event']
        assert not (terminal_seen and event.startswith('before_')), 'Action issued after native terminal'
        if event=='before_move':
            assert pending_move is None,'Second movement issued before prior ACK'
            pending_move=line
        elif event=='move_applied':
            assert pending_move is not None,'Unbound movement ACK'
            confirmed_moves.append(dict(before_line=pending_move,ack_line=line))
            pending_move=None
        elif event in ('victory','defeat'):
            terminal_seen=True
    assert pending_move is None,'Unconfirmed final movement action'
    assert terminal_seen and len(confirmed_moves)==raw['decisions']
    own_town_id=states[0][1]['towns'][0]['id']
    builds=[];recruits=[]
    for j,(line,before) in enumerate(states):
        if before['event']not in ('before_build','before_recruit'):continue
        assert j+1<len(states)
        after_line,after=states[j+1]
        assert after['event']=='economy_applied','Economic request lacks immediate successful ACK state'
        if before['event']=='before_build':
            tb={t['id']:set(t['buildings'])for t in before['towns']}
            ta={t['id']:set(t['buildings'])for t in after['towns']}
            assert set(tb)==set(ta)
            changes=[(tid,ta[tid]-tb[tid])for tid in tb if ta[tid]!=tb[tid]]
            assert len(changes)==1 and len(changes[0][1])==1,'Build changed unexpected structures'
            tid,added=changes[0]
            assert ta[tid]==tb[tid]|added
            builds.append(dict(before_line=line,after_line=after_line,day=after['day'],town=tid,
                building=next(iter(added)),gold_cost=before['gold']-after['gold']))
        else:
            before_army=total_own(before);after_army=total_own(after);gain=after_army-before_army
            assert len(gain)==1 and after_army==before_army+gain,'Recruit count delta invalid'
            cid,count=next(iter(gain.items()))
            before_available=sum(sum(t['available'])for t in before['towns'])
            after_available=sum(sum(t['available'])for t in after['towns'])
            assert before_available-after_available==count,'Recruit availability/count mismatch'
            recruits.append(dict(before_line=line,after_line=after_line,day=after['day'],creature=cid,
                count=count,gold_cost=before['gold']-after['gold']))
    first33=next((b for b in builds if b['town']==own_town_id and b['building']==33),None)
    first32=next((b for b in builds if b['town']==own_town_id and b['building']==32),None)
    recruited_types=sorted({r['creature']for r in recruits})
    transferred_types=sorted({int(c)for d in raw['deliveries']for c in d['creatures']})
    text=(native/'client.log').read_text(errors='replace').splitlines()
    query_sent=sum('Sending a request "10QueryReply"'in t for t in text)
    query_success=sum('Message 10QueryReply successfully applied!'in t for t in text)
    bad=[dict(line=i,text=t)for i,t in enumerate(text,1)if
        'has to answer queries before attempting any further actions'in t
        or ('10QueryReply'in t and any(x in t.lower()for x in ('failed','failure','unsuccess','error')))]
    assert query_sent==query_success and not bad,'Query ACK/rejection gate failed'
    mechanism_gate=bool(first33 and first32 and first33['after_line']<first32['before_line']
        and len(recruited_types)>=3 and len(transferred_types)>=3)
    return dict(schema='economy-v4-native-raw-audit-v1',passed=True,mechanism_gate_passed=mechanism_gate,
        original_town=own_town_id,first_building33=first33,first_building32=first32,
        recruited_creature_types=recruited_types,transferred_creature_types=transferred_types,
        confirmed_movement_acks=confirmed_moves,unconfirmed_final_actions=0,postterminal_actions=0,
        build_events=builds,recruit_events=recruits,query_replies_sent=query_sent,
        query_replies_successfully_applied=query_success,query_failure_lines=bad,
        scripted_economy=True,learned_economy=False,bc_eligible=0,raw=raw)
