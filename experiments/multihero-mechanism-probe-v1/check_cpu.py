#!/usr/bin/env python3
"""Synthetic gate/unit validation only. Never evidence of actual native support."""
import copy,hashlib,json,tempfile,zipfile
from pathlib import Path
from audit_run import gate
from prepare_probe import generate
HERE=Path(__file__).resolve().parent
def row(event,request=-1,result=-1):
    return dict(event=event,request_id=request,result=result,courier=0,receiver=2,query_id=10,
        pending_move=0,pending_queries=0,query_requests=0,failed=0)
def sample(transfer=True):
    events=[row('move_sent',1),row('exchange_callback')]
    if transfer:events += [row('transfer_sent',2),row('transfer_ack',2,1)]
    events += [row('close_sent',3),row('exchange_query_resolved'),row('close_ack',3,1),row('move_ack',1,1),
        row('endturn_sent',4),row('endturn_ack',4,1),row('probe_completed_nonterminal',4,1)]
    before=dict(event='probe_before_exchange',gold=1,wood=2,ore=3,
        heroes=[dict(id=0,x=0,y=0,z=0,army=[[0,10],[2,3]]),dict(id=2,x=1,y=0,z=0,army=[[0,5]])])
    after=copy.deepcopy(before);after['event']='probe_after_close'
    if transfer:after['heroes'][0]['army']=[[2,3]];after['heroes'][1]['army']=[[0,15]]
    log='DirectorAI: step hero 0 (0 0 0) -> (1 0 0) reason=PURE_ENGINEERING_actual_owned_hero_meeting\nHero courier visits receiver\nDirectorAI: step finished result=3'
    return events,[before,after],log
tests={}
for variant in ('close-only','transfer-close'):
    e,t,l=sample(variant=='transfer-close');tests[variant+'_positive_synthetic']=gate(e,t,l,variant)['engineering_pass']
def reject(name,mutate):
    e,t,l=sample();e,t,l=mutate(e,t,l)
    try:gate(e,t,l,'transfer-close');tests[name]=False
    except (AssertionError,StopIteration):tests[name]=True
reject('wrong_transfer_ack_id',lambda e,t,l:([dict(r,request_id=99) if r['event']=='transfer_ack' else r for r in e],t,l))
reject('close_before_transfer_ack',lambda e,t,l:([e[i] for i in (0,1,2,4,3,5,6,7,8,9,10)],t,l))
reject('missing_queryresolved',lambda e,t,l:([r for r in e if r['event']!='exchange_query_resolved'],t,l))
reject('missing_native_move_ack',lambda e,t,l:([r for r in e if r['event']!='move_ack'],t,l))
reject('fake_currentposition_move',lambda e,t,l:(e,t,l.replace('-> (1 0 0)','-> (0 0 0)')))
reject('failed_endturn',lambda e,t,l:([dict(r,result=0) if r['event']=='endturn_ack' else r for r in e],t,l))
def nonconserved(e,t,l):t[-1]['heroes'][1]['army']=[[0,16]];return e,t,l
reject('troop_creation',nonconserved)
def emptydonor(e,t,l):t[-1]['heroes'][0]['army']=[];return e,t,l
reject('empty_donor',emptydonor)
reject('server_rejection',lambda e,t,l:(e,t,l+'\nhas to answer queries'))
e,t,l=sample(False);negative=gate(e[:2],t[:1],l+'\nhas to answer queries','original-unhandled')
tests['original_unhandled_not_success']=not negative['engineering_pass'] and negative['winner'] is None
with tempfile.TemporaryDirectory() as temp:
    generate(Path(temp)/'one');generate(Path(temp)/'two')
    a=Path(temp)/'one';b=Path(temp)/'two'
    tests['generator_deterministic']=all((a/p.relative_to(b)).read_bytes()==p.read_bytes() for p in b.rglob('*') if p.is_file())
    for variant in ('original-unhandled','close-only','transfer-close'):
        text=(a/variant/'CDirectorAI.cpp').read_text()
        tests[variant+'_no_policy']=all(s not in text for s in ('chooseExternalCandidate','strategy-candidates-v3','request-%'))
        tests[variant+'_real_path']=all(s in text for s in ('other->visitablePos()','getPath(path','cb->moveHero(','hero->convertFromVisitablePos(step)'))
with zipfile.ZipFile(HERE/'fixture-01.vmap') as z:
    objects=json.loads(z.read('objects.json'))
    red=[r for r in objects.values() if r['type']=='hero' and r['options']['owner']=='red']
    tests['map_two_distinct_owned_heroes']=len(red)==2 and len({(r['x'],r['y'],r['l']) for r in red})==2
assert all(tests.values()),tests
report={'passed':True,'synthetic_gate_tests_only':True,'compiled':False,'installed':False,'native_games_started':0,
    'optimizer_steps':0,'tests':tests,'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(HERE/'CPU_PREPARATION_AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
