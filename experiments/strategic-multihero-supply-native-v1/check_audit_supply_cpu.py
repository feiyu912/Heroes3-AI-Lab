"""Artificial supply/log mutation checks. No real game or restoration evidence."""
import argparse,copy,json
from pathlib import Path
import audit_supply as audit

def fixture(deliver_cargo=True):
    empty=lambda:[[-1,0] for _ in range(7)]
    ma=empty();ma[0]=[0,5];ca=empty();ca[0]=[0,10];ca[1]=[2,3];ta=empty();ta[0]=[4,12]
    state=dict(schema='scripted-supply-events-v1',event='',native_request_id=-1,player=0,day=1,own_turn=1,main=8,courier=19,home=3,phase=0,query=-1,cursor=0,cycles=0,delivery_exchange=False,policy_transition=False,
               roster=[dict(id=8,position=[8,4,0],army=ma),dict(id=19,position=[2,4,0],army=ca)],towns=[dict(id=3,position=[2,4,0],visitor=19,army=ta)],pending=None,actual_request=None)
    lines=[];events=[]
    def emit(name,identity=-1,payload=None):
        e=copy.deepcopy(state);e.update(event=name,native_request_id=identity,actual_request=payload);events.append(e);lines.append('DirectorSupplyEvent '+json.dumps(e))
    emit('turn_start')
    def transact(identity,op,actor=-1,source=-1,target=-1,from_slot=-1,to_slot=-1,query=-1,exchange=False):
        command=dict(op=op,actor=actor,source=source,target=target,from_slot=from_slot,to_slot=to_slot,destination=[9,4,0])
        state['pending']=command;emit('prepared')
        kind={0:'8MoveHero',1:'13ArrangeStacks',2:'10QueryReply',3:'7EndTurn'}[op];pack={0:200,1:201,2:202,3:203}[op]
        payload=dict(request_id=identity,player=0,pack_type=pack,op={0:'MoveHero',1:'ArrangeStacks',2:'QueryReply',3:'EndTurn'}[op])
        if op==0:
            hero=next(h for h in state['roster'] if h['id']==actor);start=list(hero['position']);start[0]+=1;end=list(start);end[0]+=1
            payload.update(hero=actor,path=[end],transit=False,layer=0)
        if op==1:
            donor=next(r for r in state['roster']+state['towns'] if r['id']==source);recipient=next(r for r in state['roster']+state['towns'] if r['id']==target)
            payload.update(source=source,target=target,from_slot=from_slot,to_slot=to_slot,what=2 if recipient['army'][to_slot][1] else 1,val=0)
        if op==2:payload.update(query=query,reply=0)
        if op==3:payload['scope']='player'
        lines.extend([f'Sending a request "{kind}". It\'ll have an ID={identity}.',f'DirectorNativeRequestRegistered id={identity} player=0 pack_type={pack} type={kind}'])
        emit('native_sent',identity,payload);lines.extend(['Sending a pack of type '+kind,'Received CPack of type '+kind])
        if op==0:
            lines.append(': Hero synthetic starts movement from ('+' '.join(map(str,start))+') to ('+' '.join(map(str,end))+').')
            hero['position'][0]+=1;emit('real_move_result')
            if exchange:state.update(query=77,phase=3,delivery_exchange=True);emit('exchange_open')
        if op==1:
            creature,count=donor['army'][from_slot];donor['army'][from_slot]=[-1,0];recipient['army'][to_slot]=[creature,recipient['army'][to_slot][1]+count]
        if op==2:
            lines.extend([f"Entering void QueriesProcessor::popQuery(PlayerColor, QueryPtr): player='0', query='A query of type '20CGarrisonDialogQuery' and qid = {query} affecting player RED, '.",f'Destructed the query with id {query}'])
        lines.append('Message '+kind+' successfully applied!')
        if op in (0,3):lines.append(f'TypedActionApplied player=0 native_request_id={identity} op='+('move' if op==0 else 'end_turn')+' success=1')
        emit('real_ack',identity)
        lines.extend([f'NativeRequestAck id={identity} player=0 pack_type={pack} success=1',f'DirectorNativeRequestAck id={identity} player=0 pack_type={pack} success=1'])
        state['pending']=None
        if op==2:state.update(query=-1,phase=0,cycles=1,delivery_exchange=False)
    transact(1,0,8);transact(2,0,19);transact(3,1,19,3,19,0,2)
    state['phase']=2;transact(4,0,19,target=8,exchange=True);transact(5,1,19,19,8,2 if deliver_cargo else 0,1 if deliver_cargo else 0);transact(6,2,query=77);transact(7,0,19);transact(8,3)
    state.update(own_turn=2,day=2);emit('turn_start');transact(9,0,19)
    return events,'\n'.join(lines)+'\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();events,raw=fixture();good=audit.gate(events,raw);assert good['partial_mechanism_qualified']
    rejected=[]
    def bad(name,log=None,change=None):
        e=copy.deepcopy(events)
        if change:change(e)
        r=raw if log is None else log
        if change:
            iterator=iter(e);r='\n'.join('DirectorSupplyEvent '+json.dumps(next(iterator)) if line.startswith('DirectorSupplyEvent ') else line for line in raw.splitlines())+'\n'
        try:audit.gate(e,r)
        except (ValueError,KeyError,TypeError,IndexError):rejected.append(name)
        else:raise AssertionError('Accepted artificial invalid fixture: '+name)
    bad('mirror_mismatch',raw.replace('"main": 8','"main": 9',1))
    bad('missing_registration',raw.replace('DirectorNativeRequestRegistered id=3','BROKEN id=3'))
    bad('missing_unified_ack',raw.replace('NativeRequestAck id=3 player=0','BROKEN id=3 player=0',1))
    bad('wrong_ack_type',raw.replace('NativeRequestAck id=3 player=0 pack_type=201','NativeRequestAck id=3 player=0 pack_type=999'))
    bad('false_server_apply',raw.replace('Message 13ArrangeStacks successfully applied!','Message 13ArrangeStacks failed!',1))
    bad('missing_server_receive',raw.replace('Received CPack of type 13ArrangeStacks','BROKEN receive',1))
    bad('missing_exact_move_apply',raw.replace('TypedActionApplied player=0 native_request_id=1','BROKEN id=1'))
    bad('query_not_popped',raw.replace('20CGarrisonDialogQuery','OtherQuery'))
    bad('query_not_destroyed',raw.replace('Destructed the query with id 77','BROKEN'))
    bad('wrong_move_coordinates',raw.replace('to (10 4 0)','to (99 4 0)',1))
    bad('wrong_payload_owner',change=lambda e:next(x for x in e if x['event']=='native_sent')['actual_request'].update(player=1))
    bad('wrong_payload_source',change=lambda e:next(x for x in e if x['event']=='native_sent' and x['pending']['op']==1)['actual_request'].update(source=999))
    bad('wrong_payload_operation',change=lambda e:next(x for x in e if x['event']=='native_sent')['actual_request'].update(op='EndTurn'))
    bad('missing_native_transport',raw.replace('Sending a pack of type 13ArrangeStacks','BROKEN',1))
    bad('wrong_query_payload',change=lambda e:next(x for x in e if x['event']=='native_sent' and x['pending']['op']==2)['actual_request'].update(query=999))
    bad('army_delta_tamper',change=lambda e:next(x for x in e if x['event']=='real_ack' and x['native_request_id']==3)['towns'][0]['army'][0].__setitem__(1,1))
    bad('role_drift',change=lambda e:e[-1].update(courier=20))
    bad('policy_claim',change=lambda e:e[-1].update(policy_transition=True))
    bad('own_turn_phase_reset',change=lambda e:next(x for x in e if x['event']=='turn_start' and x['own_turn']==2).update(phase=1))
    bad('closed_query_still_live',change=lambda e:next(x for x in e if x['event']=='prepared' and x['pending']['actor']==19 and x['cycles']==1).update(query=77))
    # A valid interrupted suffix retains no invented ACK or global success.
    cutoff=raw.index('Message 7EndTurn successfully applied!');partial=raw[:cutoff]
    pe=[x['event'] for x in audit.parse(partial)[0]];tail=audit.gate(pe,partial)
    assert tail['incomplete_tail'] and 8 in tail['owned_registered_unacked_ids']
    wrong_events,wrong_raw=fixture(False);wrong_goal=audit.gate(wrong_events,wrong_raw)
    assert wrong_goal['generic_transfer_mechanisms_qualified'] and not wrong_goal['cargo_goal_qualified'] and not wrong_goal['partial_mechanism_qualified']
    a.out.mkdir(parents=True,exist_ok=False);r=dict(passed=True,fixture=True,real_execution_certified=False,new_native_games=0,GPU_operations=0,optimizer_steps=0,rejected=rejected,partial_tail_preserved=True,
        source_sha256={str(p):audit.sha(p) for p in [Path(__file__),Path(audit.__file__)]})
    r['legal_transfer_without_cargo_delivery_rejected_as_logistics_success']=True
    (a.out/'AUDIT.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
if __name__=='__main__':main()
