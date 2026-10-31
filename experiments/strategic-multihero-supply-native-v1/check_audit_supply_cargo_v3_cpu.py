"""Artificial cargo ledger/ACK tests; no native execution or expert evidence."""
import argparse,copy,json
from pathlib import Path
from check_audit_supply_cpu import fixture as old_fixture
import audit_supply_cargo_v3 as audit

def fixture():
    _,raw=old_fixture(True);events=[];lines=[]
    reserve=[[-1,0],[2,3]]+[[-1,0] for _ in range(5)]
    job=dict(id=0,status=0,successful_jobs=0,incomplete_attempts=0,success=False,reason='synthetic_explicit_fixture',initial_reserve_slots=reserve,cargo_slots=[[-1,0] for _ in range(7)],reserve=[[2,3]],picked=[],cargo_remaining=[],delivered=[])
    for line in raw.splitlines():
        if not line.startswith('DirectorSupplyEvent '):lines.append(line);continue
        e=json.loads(line.split('DirectorSupplyEvent ',1)[1]);e['schema']='scripted-supply-events-v3';e['controller_epoch']='scripted-supply-cargo-v3'
        for row in e['roster']+e['towns']:
            if row['id']==19:
                row['army'][0]=[-1,0]
                if row['army'][2][1]:row['army'][2]=[0,10]
            if row['id']==3 and row['army'][0][1]:row['army'][0]=[0,10]
            if row['id']==8 and row['army'][1][1]:row['army'][1]=[-1,0];row['army'][0]=[0,15]
        if e['pending'] and e['pending']['op']==1 and e['pending']['source']==19:e['pending']['to_slot']=0
        p=e.get('actual_request')
        if p and p['op']=='ArrangeStacks' and p['source']==19:p.update(to_slot=0,what=2)
        e['job']=copy.deepcopy(job);events.append(e);lines.append('DirectorSupplyEvent '+json.dumps(e))
        if e['event']=='real_ack':
            identity=e['native_request_id']
            if identity==3:job.update(id=1,status=1,picked=[[0,10]],cargo_remaining=[[0,10]],cargo_slots=[[-1,0],[-1,0],[0,10]]+[[-1,0] for _ in range(4)])
            if identity==5:job.update(delivered=[[0,10]],cargo_remaining=[],cargo_slots=[[-1,0] for _ in range(7)])
            if identity==6:job.update(status=2,successful_jobs=1,success=True)
            after=copy.deepcopy(e);after.update(event='control_ack_applied',pending=None,job=copy.deepcopy(job))
            if identity==6:after.update(query=-1,phase=0,cycles=1,delivery_exchange=False)
            events.append(after);lines.append('DirectorSupplyEvent '+json.dumps(after))
    return events,'\n'.join(lines)+'\n'

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();events,raw=fixture();good=audit.gate(events,raw)
    assert good['partial_mechanism_qualified'] and good['fixture_cargo_flow_qualified'] and len(good['certified_successful_jobs'])==1
    rejected=[]
    def reject(name,change):
        e=copy.deepcopy(events);change(e);iterator=iter(e)
        log='\n'.join('DirectorSupplyEvent '+json.dumps(next(iterator)) if s.startswith('DirectorSupplyEvent ') else s for s in raw.splitlines())+'\n'
        try:audit.gate(e,log)
        except (ValueError,KeyError,TypeError,IndexError):rejected.append(name)
        else:raise AssertionError('Accepted invalid synthetic cargo ledger '+name)
    reject('cargo_registered_before_pickup_ACK',lambda e:next(x for x in e if x['event']=='native_sent' and x['native_request_id']==3)['job'].update(cargo_remaining=[[0,10]]))
    reject('picked_counter_without_native_ACK',lambda e:e[0]['job'].update(picked=[[0,10]]))
    reject('initial_reserve_changed',lambda e:e[-1]['job']['initial_reserve_slots'][1].__setitem__(1,2))
    reject('reserve_ledger_tampered',lambda e:e[-1]['job'].update(reserve=[[2,2]]))
    reject('cargo_slot_false_contribution',lambda e:next(x for x in e if x['event']=='control_ack_applied' and x['native_request_id']==3)['job']['cargo_slots'][2].__setitem__(1,9))
    reject('success_before_close_ACK',lambda e:next(x for x in e if x['event']=='real_ack' and x['native_request_id']==6)['job'].update(status=2,successful_jobs=1,success=True))
    reject('successful_count_only',lambda e:e[-1]['job'].update(successful_jobs=999))
    reject('delivered_counter_only',lambda e:e[-1]['job'].update(delivered=[[0,11]]))
    reject('wrong_job_id',lambda e:e[-1]['job'].update(id=2))
    reject('wrong_status',lambda e:e[-1]['job'].update(status=3))
    reject('wrong_controller_epoch',lambda e:e[-1].update(controller_epoch='legacy'))
    reject('missing_control_ACK_identity',lambda e:next(x for x in e if x['event']=='control_ack_applied').update(native_request_id=999))
    reject('native_reserve_lost',lambda e:e[-1]['roster'][1]['army'][1].__setitem__(1,2))
    reject('cargo_booked_at_prepared',lambda e:next(x for x in e if x['event']=='prepared' and x['pending']['op']==1)['job'].update(picked=[[0,10]]))
    broken=raw.replace('DirectorNativeRequestAck id=6 player=0','MISSING id=6 player=0')
    try:audit.gate(events,broken)
    except ValueError:rejected.append('missing_middle_ACK_is_not_EOF')
    else:raise AssertionError('Middle ACK ledger gap accepted as EOF')
    # A compatible-but-incomplete close has no success certificate. This tests
    # the ledger subpredicate only; it supplies no native execution evidence.
    incomplete=[]
    for e in copy.deepcopy(events):
        c=e.get('pending')
        if e['native_request_id']==5 or (c and c['op']==1 and c['source']==19):continue
        j=e['job']
        if j['id']==1:
            next(h for h in e['roster'] if h['id']==8)['army'][0]=[0,5]
            next(h for h in e['roster'] if h['id']==19)['army'][2]=[0,10]
            was_closed=j['status']==2
            j.update(delivered=[],cargo_remaining=[[0,10]],cargo_slots=[[-1,0],[-1,0],[0,10]]+[[-1,0] for _ in range(4)],
                     successful_jobs=0,success=False,status=3 if was_closed else 1,incomplete_attempts=1 if was_closed else 0)
        incomplete.append(e)
    negative=audit.cargo_gate(incomplete,{'completed_transactions':[t for t in good['completed_transactions'] if t['id']!=5]})
    assert not negative['certified_successful_jobs'] and negative['reconstructed_incomplete_attempts']==1 and negative['cargo_remaining']=={0:10}
    a.out.mkdir(parents=True,exist_ok=False);r=dict(passed=True,fixture=True,real_execution_certified=False,new_native_games=0,GPU_operations=0,optimizer_steps=0,positive_explicit_cargo_case=True,rejected=rejected,
       source_sha256={str(p):audit.sha(p) for p in [Path(__file__),Path(audit.__file__),Path(__file__).with_name('check_audit_supply_cpu.py')]})
    r['incomplete_close_preserves_cargo_without_success']=True
    (a.out/'AUDIT.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
if __name__=='__main__':main()
