"""Synthetic checkpoint predicate tests, never native hydration certification."""
import argparse,copy,hashlib,json
from pathlib import Path
import checkpoint_predicates as p

def sample():
    reserve=[[2,3]]+[[-1,0] for _ in range(6)];cargo=[[-1,0],[0,10]]+[[-1,0] for _ in range(5)]
    job=dict(id=1,status=1,successful_jobs=0,incomplete_attempts=0,success=False,reason='synthetic_fixture',initial_reserve_slots=reserve,cargo_slots=cargo,reserve=[[2,3]],picked=[[0,10]],cargo_remaining=[[0,10]],delivered=[])
    control=dict(main=0,courier=2,home=3,turn=2,cursor=1,cycles=0,phase=2,spent={'0':1},blocked={},goals={'0':[9,6,0],'2':[9,7,0]},visited=[[9,7,0]],job_state=job)
    boundary=dict(pending_request=None,movement_busy=False,battle_busy=False,native_query_open=False,owned_request_count=0,queued_own_turn=False)
    return control,boundary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();c,b=sample();p.carrying_control(c);p.boundary(b)
    rejected=[]
    def reject(name,fn):
        try:fn()
        except (ValueError,KeyError,TypeError):rejected.append(name)
        else:raise AssertionError('Accepted invalid synthetic checkpoint '+name)
    for field,bad in [('pending_request',3),('movement_busy',True),('battle_busy',True),('native_query_open',True),('queued_own_turn',True),('owned_request_count',1),('owned_request_count',False)]:
        value=dict(b);value[field]=bad;reject('dirty_boundary_'+field+'_'+str(bad),lambda value=value:p.boundary(value))
    for field,bad in [('turn',1),('spent',{}),('cursor',False),('visited',[]),('goals',{})]:
        value=copy.deepcopy(c);value[field]=bad;reject('trivial_or_invalid_control_'+field,lambda value=value:p.carrying_control(value))
    value=copy.deepcopy(c);value['job_state']['cargo_slots'][1][1]=9;reject('slot_count_not_species_ledger',lambda:p.carrying_control(value))
    value=copy.deepcopy(c);value['job_state']['picked']=[[0,9]];reject('cargo_not_pickup_conserved',lambda:p.carrying_control(value))
    value=copy.deepcopy(c);value['job_state']['status']=True;reject('boolean_job_status',lambda:p.carrying_control(value))
    world={'actual_owned_heroes':[0,2],'day':2};p.restore_equality(c,world,c,world,c,world)
    value=copy.deepcopy(c);value['turn']+=1;reject('hydrate_incremented_turn',lambda:p.restore_equality(c,world,c,world,value,world))
    value=copy.deepcopy(c);value['spent']={};reject('hydrate_cleared_budget',lambda:p.restore_equality(c,world,c,world,value,world))
    value=copy.deepcopy(c);value['cursor']=0;reject('hydrate_reselected_actor',lambda:p.restore_equality(c,world,c,world,value,world))
    value=copy.deepcopy(c);value['job_state']['cargo_remaining']=[];reject('hydrate_lost_cargo',lambda:p.restore_equality(c,world,c,world,value,world))
    reject('hydrate_world_mismatch',lambda:p.restore_equality(c,world,c,world,c,dict(world,day=3)))
    continuation=[dict(own_turn=2,action={'op':'MoveHero','hero':2,'path':[[8,9,0]]},native_transaction_completed=True),dict(own_turn=3,action={'op':'ArrangeStacks','source':2,'target':0,'count':10},native_transaction_completed=True)]
    p.continuation(continuation,continuation)
    reject('missing_EOF_continuation',lambda:p.continuation(continuation,continuation[:1]))
    other=copy.deepcopy(continuation);other[0]['action']['hero']=0;reject('different_actor_after_hydrate',lambda:p.continuation(continuation,other))
    other=copy.deepcopy(continuation);other[0]['native_transaction_completed']=False;reject('uncompleted_native_action',lambda:p.continuation(other,other))
    local=dict(id=20,player=0,pack_type=179,op='SaveLocalState',success=True,registered_line=10,bound_line=11,server_apply_line=20,callback_line=30,unified_ack_line=45,director_ack_line=46)
    save=dict(id=21,player=0,pack_type=178,op='SaveGame',success=True,registered_line=31,bound_line=32,server_apply_line=60,callback_line=70,unified_ack_line=80,director_ack_line=81)
    data=b'VCMI'+b'SYNTHETIC NOT A GAME'*4;digest=hashlib.sha256(data).hexdigest();p.save_chain(local,save,59,data,digest)
    reject('save_ACK_without_file',lambda:p.save_chain(local,save,59,b'',digest))
    reject('save_ACK_wrong_file_SHA',lambda:p.save_chain(local,save,59,data,'0'*64))
    reject('save_success_log_after_ACK',lambda:p.save_chain(local,save,71,data,digest))
    bad=dict(save,bound_line=29);reject('save_before_localstate_ACK',lambda:p.save_chain(local,bad,59,data,digest))
    bad=dict(save,unified_ack_line=69);reject('unified_ACK_before_callback',lambda:p.save_chain(local,bad,59,data,digest))
    a.out.mkdir(parents=True,exist_ok=False);result=dict(passed=True,fixture=True,native_execution_certified=False,native_hydration_certified=False,new_native_games=0,GPU_operations=0,rejected=rejected,
        valid_callback_dispatched_next_save_before_previous_unified_ACK=True,source_sha256={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [Path(__file__),Path(p.__file__)]},
        limitation='Pure CPU predicates only. Actual supply-v4 event adapter/raw/native source and file/load bindings remain required.')
    (a.out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
