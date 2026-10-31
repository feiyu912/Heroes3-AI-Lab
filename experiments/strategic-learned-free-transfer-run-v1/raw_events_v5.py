"""Owned-player raw event extraction. Retains immutable native request binding."""
import json,re
from audit_contract import BINDING
def extract(raw,owned):
    assert type(owned) is int and owned in (0,1)
    events=[];client_events=[];bindings={};lines=[];foreign=[]
    for number,line in enumerate(raw.splitlines(),1):
        line=re.sub(r'\x1b\[[0-9;]*m','',line)
        if 'DirectorTypedEvent ' in line:
            event=json.loads(line.split('DirectorTypedEvent ',1)[1])
            assert event['player']==owned and event['event']!='typed_protocol_error'
            client_events.append(event)
            if event['event']=='native_action_sent':
                key=(event['player'],event['native_request_id'],event['op'])
                assert key not in bindings;bindings[key]=event
            events.append(event);lines.append(number)
        elif 'TypedActionApplied ' in line:
            m=re.search(r'TypedActionApplied player=(\d+) native_request_id=(\d+) op=(move|end_turn|build) success=([01])$',line)
            assert m,'Malformed actual server apply marker'
            player,identity,op,success=int(m[1]),int(m[2]),m[3],int(m[4]);key=(player,identity,op)
            if player!=owned:foreign.append(dict(line=number,player=player,request_id=identity,success=success));continue
            assert success==1 and key in bindings,'Unbound/rejected actual server apply'
            event={k:bindings[key][k] for k in BINDING};event.update(event='server_action_applied',source='server',success=True)
            events.append(event);lines.append(number)
    return events,client_events,lines,foreign

