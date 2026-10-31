"""Independent actual raw reconstruction; never launch games or import Torch."""
from pathlib import Path
import json,hashlib,sys,collections,os,fcntl
OUT=Path(__file__).resolve().parent
EXP=OUT.parent;NATIVE=EXP/'native-01';TOOLS=EXP.parent/'strategic-refill-retention-qualification-20261025'
sys.path.insert(0,str(TOOLS))
import common
import audit_mechanism as registered
import audit_pair as registered_pair

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s]
def write(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def totals(a):
 c=collections.Counter()
 for s in a:
  if s:c[s['creature_id']]+=s['count']
 return dict(c)
def one(events,event,**keys):
 rows=[(i,e) for i,e in enumerate(events) if e['event']==event and all(e.get(k)==v for k,v in keys.items())];assert len(rows)==1,(event,keys,len(rows));return rows[0]
def main():
 handles=[]
 try:
  for p in common.leases.PATHS:
   assert p.is_file();f=p.open('r');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(f)
  write(OUT/'LEASES.json',dict(order=['GPU','pool'],entries=[common.leases.metadata(f,p) for f,p in zip(handles,common.leases.PATHS)],independent_read_only=True))
  games=[];byname={};inputs={};replayed=[];contract=load(common.CONTRACT)
  for arm in ('baseline','candidate'):
   for case in ('positive','empty','full-incompatible','full-merge'):
    d=NATIVE/(arm+'-'+case);plan=load(d/'PLAN.json');events=lines(d/'typed.jsonl');records=lines(d/'agent/mechanism-selector.jsonl');log=(d/'client.log').read_text();trace=lines(d/'strategy-trace.jsonl')
    # Rerun registered checks from frozen code, not old AUDIT flags.
    result=registered.audit(d);assert result['passed'];replayed.append(dict(game=d.name,actual_decisions_checked=result['actual_decisions_checked'],actual_recruits_checked=result['actual_recruits_checked'],actual_transfers_checked=result['actual_transfers_checked']))
    selected=[]
    for i,r in enumerate(records,1):
     q=r['request'];response=r['response'];assert q==load(d/f'agent/request-{i:08d}.json');assert response==load(d/f'agent/action-{i:08d}.json');assert response['request_sha256']==sha(d/f'agent/request-{i:08d}.json');c=q['candidates'][response['selected_index']]
     si,s=one(events,'native_action_sent',decision_id=i);ai,a=one(events,'package_applied',decision_id=i)
     assert si<ai and a['success'] is True and s['native_request_id']==a['native_request_id']
     assert s['candidate']==a['candidate']==c and s['request_sha256']==a['request_sha256']==response['request_sha256']
     selected.append((q,c))
    prefix=[]
    for q,c in selected:
     prefix.append((q,c))
     if c['op']=='end_turn':break
    q0=prefix[0][0];home=next(t for t in q0['own_towns'] if t['position']==q0['from']);tid=home['town_id'];hero=q0['hero'];initial=home['recruit_state'];assert initial['visitor']['hero_id']==hero and initial['owner']==q0['player'] and not any(initial['upper_army'])
    moveproof=[]
    for i,(q,c) in enumerate(prefix):
     if c['op']!='move':continue
     mi,m=one(events,'move_result',decision_id=q['request_id']);si,s=one(events,'native_action_sent',decision_id=q['request_id']);ai,a=one(events,'package_applied',decision_id=q['request_id']);assert si<mi<ai
     assert m['result']==1 and m['candidate']==c and m['native_request_id']==s['native_request_id'] and m['evidence']=='received_TryMoveHero'
     assert prefix[i+1][0]['from']==c['next'] and q['from']!=c['next']
     assert any(t['event']=='move_applied' and t['own_turn']==q['own_turn'] and any(h['id']==hero and [h['x'],h['y'],h['z']]==c['next'] for h in t['heroes']) for t in trace)
     moveproof.append(dict(decision_id=q['request_id'],native_request_id=s['native_request_id'],from_position=q['from'],to_position=c['next'],kind=c['kind']))
    transfers=[]
    for ti,t in enumerate(events):
     if t['event']!='free_transfer_native_sent':continue
     ai,a=one(events,'free_transfer_ack_state',native_request_id=t['native_request_id']);assert ai>ti and a['success'] and a['state_change_verified'] and a['before_state']==t['before_state'];b=a['before_state'];s=a['state'];cr=t['creature_id'];amount=t['amount']
     assert b['resources']==s['resources'] and b['recruit_stock']==s['recruit_stock'] and b['buildings']==s['buildings'] if 'buildings' in b else b['resources']==s['resources'] and b['recruit_stock']==s['recruit_stock']
     sourcebefore=totals(b['upper_army']);sourceafter=totals(s['upper_army']);targetbefore=totals(b['visitor']['army']);targetafter=totals(s['visitor']['army'])
     expectedsource=dict(sourcebefore);expectedsource[cr]-=amount;expectedsource={k:v for k,v in expectedsource.items() if v};expectedtarget=dict(targetbefore);expectedtarget[cr]=expectedtarget.get(cr,0)+amount
     assert sourceafter==expectedsource and targetafter==expectedtarget and t['source_army_id']==b['upper_army_id'] and t['target_army_id']==b['visitor']['hero_id']==hero
     transfers.append(dict(native_request_id=t['native_request_id'],creature_id=cr,amount=amount,what=t['actual_what'],source_before=sourcebefore,source_after=sourceafter,target_before=targetbefore,target_after=targetafter,occupied_slots_before=sum(s is not None for s in b['visitor']['army']),occupied_slots_after=sum(s is not None for s in a['state']['visitor']['army'])))
    counts=collections.Counter(c['op'] for q,c in selected);sent=[e for e in events if e['event']=='native_action_sent'];acks=[e for e in events if e['event']=='package_applied'];assert len(sent)==len(acks)==len(records) and all(e['success'] for e in acks)
    terminal=one(events,'game_over',player=plan['owned_player'])[1];assert terminal['completed'] and terminal['own_turn']==3
    assert len([e for e in events if e['event']=='your_turn'])==3
    capsule=Path(plan['capsule']);bins=load(capsule/'binary-sha256.json');assert all(sha(capsule/'bin'/n)==h for n,h in bins.items())
    for f in d.rglob('*'):
     if f.is_file() and not f.is_symlink():inputs[str(f)]=sha(f)
    row=dict(game=d.name,arm=arm,case=case,decision_count=len(records),selected_ops=dict(counts),actual_move_results=len([e for e in events if e['event']=='move_result']),typed_action_acks=len(acks),recruit_ack_states=len([e for e in events if e['event']=='recruit_ack_state']),free_transfer_acks=len(transfers),first_turn_sequence=[c['op'] for q,c in prefix],move_proof=moveproof,transfers=transfers,initial_occupied_slots=sum(s is not None for s in initial['visitor']['army']),terminal=terminal,drain=result['drain'],binary_sha256=bins,compiled_source_manifest_sha256=sha(capsule/'build-source-manifest.json'),loaded_observation_count=len(load(d/'EXECUTION.json')['loaded_library_observations']),seed=plan['seed'],map=plan['map'])
    games.append(row);byname[d.name]=(records,row)
  pairs=[]
  for case in ('positive','empty','full-incompatible','full-merge'):
   b,br=byname['baseline-'+case];c,cr=byname['candidate-'+case];registered_result=registered_pair.pair(NATIVE/('baseline-'+case),NATIVE/('candidate-'+case));assert registered_result['passed']
   assert b[0]['request']==c[0]['request'] and b[0]['response']==c[0]['response'];assert b[1]['request']==c[1]['request'] and b[1]['response']==c[1]['response']
   added=None
   if case in ('positive','full-merge'):
    bq=b[2]['request'];cq=c[2]['request'];assert {k:v for k,v in bq.items() if k!='candidates'}=={k:v for k,v in cq.items() if k!='candidates'}
    assert cq['candidates'][0]==bq['candidates'][0] and cq['candidates'][2:]==bq['candidates'][1:] and len(cq['candidates'])==len(bq['candidates'])+1
    added=cq['candidates'][1];assert added['op']=='move' and added['kind']==4 and added['position']==c[0]['request']['from']
    assert c[2]['response']['selected_index']==0 and c[3]['request']['candidates'][c[3]['response']['selected_index']]['kind']==4
    assert len(cr['move_proof'])==4 and len(cr['transfers'])==1
    assert br['free_transfer_acks']==0
    if case=='full-merge':assert cr['initial_occupied_slots']==7 and cr['transfers'][0]['what']==2 and cr['transfers'][0]['occupied_slots_before']==cr['transfers'][0]['occupied_slots_after']==7
   else:
    n=2 if case=='empty' else 3;assert all(b[i]['request']==c[i]['request'] and b[i]['response']==c[i]['response'] for i in range(n));assert cr['free_transfer_acks']==br['free_transfer_acks']==0
    if case=='full-incompatible':assert cr['initial_occupied_slots']==br['initial_occupied_slots']==7
   pairs.append(dict(case=case,passed=True,exact_prefix=True,added_candidate=added,positive_transfer=bool(added)))
  bm=load(Path(contract['capsule_root'])/'baseline/build-source-manifest.json');cm=load(Path(contract['capsule_root'])/'candidate/build-source-manifest.json');assert set(bm)==set(cm);changed=[p for p in bm if bm[p]!=cm[p]];assert changed==['AI/DirectorAI/CDirectorAI.cpp']
  allcounts=collections.Counter()
  for g in games:allcounts.update(g['selected_ops'])
  assert 'torch' not in sys.modules
  result=dict(passed=True,scope='eight existing diagnostic native games/four matched cases; raw independent mechanism proof, no ability/strength claim',games=games,pairs=pairs,source_changes=changed,totals=dict(existing_games=len(games),actual_decisions=sum(g['decision_count'] for g in games),selected_ops=dict(allcounts),successful_move_results=sum(g['actual_move_results'] for g in games),typed_action_acks=sum(g['typed_action_acks'] for g in games),recruit_ack_states=sum(g['recruit_ack_states'] for g in games),free_transfer_acks=sum(g['free_transfer_acks'] for g in games),completed_calendar_games=8),frozen_auditors_reexecuted=replayed,deferred_boundaries=load(TOOLS/'FIXTURE_MANIFEST.json')['deferred_boundaries'],new_native_games=0,new_optimizer_steps=0,torch_imported=False,final_test_used=False,strength_claim=False,model_promoted=False)
  write(OUT/'AUDIT.json',result);write(OUT/'RAW_SHA256.json',inputs);print(json.dumps(result['totals'],indent=2))
 finally:
  for f in reversed(handles):fcntl.flock(f,fcntl.LOCK_UN);f.close()
if __name__=='__main__':main()
