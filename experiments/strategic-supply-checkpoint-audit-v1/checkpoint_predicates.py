"""Strict CPU predicates for checkpoint evidence adapters, not a native certificate.

The native event adapter is deliberately separate until supply-v4 schema freezes.
No caller can obtain a native certification from these synthetic predicates alone.
"""
import collections,hashlib,json

CONTROL_KEYS={'main','courier','home','turn','cursor','cycles','phase','spent','blocked','goals','visited','job_state'}
BOUNDARY_KEYS={'pending_request','movement_busy','battle_busy','native_query_open','owned_request_count','queued_own_turn'}
JOB_KEYS={'id','status','successful_jobs','incomplete_attempts','success','reason','initial_reserve_slots','cargo_slots','reserve','picked','cargo_remaining','delivered'}

def require(ok,message):
    if not ok:raise ValueError(message)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()

def pairs(values,slot=False):
    require(isinstance(values,list) and (not slot or len(values)==7),'Invalid ledger/slot array')
    result=collections.Counter()
    for p in values:
        require(isinstance(p,list) and len(p)==2 and all(type(n) is int for n in p),'Invalid integer pair')
        creature,count=p;require(count>=0 and (not count or creature>=0),'Invalid creature count')
        if not slot:require(count>0 and creature not in result,'Duplicate/empty species entry')
        if count:result[creature]+=count
    return result

def boundary(value):
    require(set(value)==BOUNDARY_KEYS,'Incomplete/unknown boundary fields')
    require(value['pending_request'] is None,'Live strategy request')
    require(type(value['owned_request_count']) is int and value['owned_request_count']==0,'Logically unacknowledged owned request')
    for k in BOUNDARY_KEYS-{'pending_request','owned_request_count'}:require(value[k] is False,'Live native boundary '+k)

def carrying_control(c):
    require(set(c)==CONTROL_KEYS,'Incomplete/unknown persistent control fields')
    for k in ['main','courier','home','turn','cursor','cycles','phase']:require(type(c[k]) is int,'Noninteger control '+k)
    require(c['main']>=0 and c['courier']>c['main'] and c['home']>=0,'Invalid saved roles')
    require(c['turn']==2 and c['cursor'] in (0,1) and c['phase'] in (0,1,2) and c['cycles']>=0,'Not target midturn2 boundary')
    roles={str(c['main']),str(c['courier'])}
    for k in ['spent','blocked','goals']:require(isinstance(c[k],dict) and set(c[k])<=roles,'Invalid per-actor map '+k)
    require(all(type(n) is int and 0<=n<=54 for n in c['spent'].values()) and any(n>0 for n in c['spent'].values()),'No nonzero current-turn budget evidence')
    require(c['visited'] and c['goals'],'Empty day1-like controller history')
    j=c['job_state'];require(isinstance(j,dict) and set(j)==JOB_KEYS,'Incomplete/unknown saved cargo job')
    require(all(type(j[k]) is int and j[k]>=0 for k in ['id','status','successful_jobs','incomplete_attempts']),'Noninteger saved job counter')
    reserve=pairs(j['reserve']);cargo=pairs(j['cargo_remaining']);picked=pairs(j['picked']);delivered=pairs(j['delivered'])
    require(reserve and cargo and picked==cargo+delivered,'No actual carrying ledger or broken cargo conservation')
    require(pairs(j['initial_reserve_slots'],True)==reserve and pairs(j['cargo_slots'],True)==cargo,'Slot/species state mismatch')
    require(j['success'] is False and j['status']==1 and j['successful_jobs']==0,'Checkpoint must carry unfinished cargo')

def restore_equality(saved_control,saved_world,loaded_control,loaded_world,hydrated_control,hydrated_world):
    carrying_control(saved_control)
    require(canonical(saved_control)==canonical(loaded_control)==canonical(hydrated_control),'Saved/loaded/hydrated C++ control mismatch')
    require(canonical(saved_world)==canonical(loaded_world)==canonical(hydrated_world),'Saved/loaded/hydrated own-world mismatch')

def continuation(left,right):
    """Adapters supply semantic native action/world/control records, no IDs/times."""
    require(left and right,'Empty continuation')
    require(len(left)==len(right),'Continuation EOF mismatch')
    require(canonical(left)==canonical(right),'Native action/world/control continuation mismatch')
    turns={r['own_turn'] for r in left}
    require(min(turns)==2 and max(turns)>=3,'Continuation never crosses saved own turn')
    require(all(r['native_transaction_completed'] is True for r in left),'Unfinished action cannot be compared as executed')
    return dict(projected_continuation_equal=True,records=len(left),own_turns=sorted(turns),complete_hidden_world_equality=False)

def save_chain(local,save,successful_save_line,save_bytes,recorded_sha):
    """Check normalized real-log facts; adapter must prove where each came from."""
    for transaction in [local,save]:
        require(type(transaction['id']) is int and transaction['id']>0 and transaction['player']==0,'Invalid checkpoint native identity')
        require(type(transaction['pack_type']) is int and transaction['pack_type']>0 and transaction['success'] is True,'Invalid checkpoint actual ACK')
        order=[transaction[k] for k in ['registered_line','bound_line','server_apply_line','callback_line','unified_ack_line','director_ack_line']]
        require(all(type(n) is int and n>0 for n in order) and order==sorted(set(order)),'Checkpoint callback/actual ACK ordering invalid')
    require(local['op']=='SaveLocalState' and save['op']=='SaveGame' and local['id']!=save['id'],'Checkpoint request kinds/IDs invalid')
    # The next send can occur inside the previous callback, before unified ACK
    # logging and registry removal. Requiring the latter first would be wrong.
    require(local['callback_line']<save['bound_line'],'SaveGame precedes received SaveLocalState ACK')
    require(save['bound_line']<successful_save_line<save['callback_line'],'No actual successful file write before SaveGame ACK')
    require(isinstance(save_bytes,bytes) and len(save_bytes)>=64 and save_bytes[:4]==b'VCMI','Missing/malformed native binary save')
    require(hashlib.sha256(save_bytes).hexdigest()==recorded_sha,'Save binary SHA mismatch')
    return dict(checkpoint_request_predicates_valid=True,native_execution_certified=False)
