"""Independent missing-boundary checks layered on complete native transport proof."""
import argparse,collections,json,zipfile
from pathlib import Path
from boundary_common import HERE,fixture,load,sha,write,verify_source_freeze
# boundary_common prepends V1; explicit file loading avoids accidental auditor reuse.
import importlib.util
spec=importlib.util.spec_from_file_location('_boundary_raw',HERE/'boundary_raw_contract.py');raw=importlib.util.module_from_spec(spec);spec.loader.exec_module(raw)
from prepare_fixtures import land_connected

def one(rows,predicate):
 hits=[(i,r) for i,r in enumerate(rows) if predicate(r)];assert len(hits)==1,len(hits);return hits[0]
def movement(q):return [c for c in q['candidates'] if c['op']=='move']
def goal(c):return (c['position'],c['kind'])
def target(q,pos):return [t for t in q['own_towns'] if t['position']==pos]
def audit(work):
 verify_source_freeze();work=Path(work);plan=load(work/'PLAN.json');execution=load(work/'EXECUTION.json');manifest,f=fixture(plan['case'])
 assert plan['classification']=='diagnostic_only' and plan['training_samples']==plan['optimizer_steps']==0 and plan['checkpoint'] is None
 assert execution['passed'] and execution['owned_children_cleaned_before_release']
 for k in ['seed','owned_player','opponent','action_schema']:assert plan[k]==f['schema' if k=='action_schema' else k]
 for proof in [load(work/'NATIVE_LEASES.json'),load(work/'agent/BROKER_LEASES.json')]:assert proof['inherited_flock_verified'] and proof['entries']==plan['resource_locks']
 assert len(execution['native_inherited_fd_observations'])==2
 for observed,expected in zip(execution['native_inherited_fd_observations'],plan['resource_locks']):assert all(observed[k]==expected[k] for k in ['fd','device','inode'])
 result=raw.audit_game(work,HERE,mechanism=False);events=raw.lines(work/'typed.jsonl');records=raw.lines(work/'agent/mechanism-selector.jsonl');trace=raw.lines(work/'strategy-trace.jsonl')
 assert len(records)==result['actual_decisions_checked'] and [r['request']['request_id'] for r in records]==list(range(1,len(records)+1))
 selected=[]
 for i,r in enumerate(records,1):
  q=r['request'];a=r['response'];assert q==load(work/f'agent/request-{i:08d}.json') and a==load(work/f'agent/action-{i:08d}.json')
  assert a['classification']=='diagnostic_only' and r['mechanism_only'] and not r['neural_network'] and not (r['coverage_note'] or '').startswith('uncovered:')
  selected.append((q,q['candidates'][a['selected_index']]))
 prefix=[]
 for row in selected:
  prefix.append(row)
  if row[1]['op']=='end_turn':break
 assert prefix[-1][1]=={'op':'end_turn'} and len({q['own_turn'] for q,c in prefix})==1
 assert all(c=={'op':'end_turn'} for q,c in selected[len(prefix):])
 for index,event in enumerate(events):
  if event['event']=='native_action_sent' and event['player']==1:
   previous=[e for e in events[:index] if e['event']=='busy_state' and e['player']==1]
   assert previous and previous[-1]['query_count']==0 and not any(previous[-1][k] for k in ['movement_busy','economy_busy','battle_busy'])
 terminal_i,_=one(events,lambda e:e['event']=='game_over' and e.get('completed') is True and e['player']==1)
 busy=[e for e in events[:terminal_i] if e['event']=='busy_state' and e['player']==1];assert busy and busy[-1]['query_count']==0 and not any(busy[-1][k] for k in ['movement_busy','economy_busy','battle_busy'])
 q0,c0=prefix[0];qend,cend=prefix[-1];home=f['target_town_position'];case=plan['case']
 assert q0['from']==f['expected_initial_hero_position']
 starts=[t for t in trace if t['event']=='before_move' and t['own_turn']==q0['own_turn'] and any(h['id']==q0['hero'] and [h['x'],h['y'],h['z']]==q0['from'] for h in t['heroes'])];assert starts
 h0=one(starts[0]['heroes'],lambda h:h['id']==q0['hero'])[1];initial_army=dict(h0['army']);assert initial_army
 moves_proven=[]
 for i,(q,c) in enumerate(prefix[:-1]):
  assert c['op']=='move';rid=q['request_id'];si,s=one(events,lambda e:e['event']=='native_action_sent' and e.get('decision_id')==rid)
  mi,m=one(events,lambda e:e['event']=='move_result' and e.get('decision_id')==rid);ai,a=one(events,lambda e:e['event']=='package_applied' and e.get('decision_id')==rid)
  assert si<mi<ai and m['candidate']==c and m['source']=='server' and m['evidence']=='received_TryMoveHero' and a['success'] is True
  nq=prefix[i+1][0]
  if m['result']==1:assert nq['from']==c['next'] and nq['from']!=q['from']
  else:assert case=='consumed-pickup' and m['result']==3 and i==len(prefix)-2 and c['position']==[26,11,0]
  assert any(t['event']=='move_applied' and t['own_turn']==q['own_turn'] and any(h['id']==q['hero'] and [h['x'],h['y'],h['z']]==nq['from'] for h in t['heroes']) for t in trace)
  moves_proven.append(dict(decision_id=rid,result=m['result'],actual_before=q['from'],actual_after=nq['from'],native_request_id=s['native_request_id']))
 facts={}
 if case in ('reachable-stock-control','unreachable-stock','nonowned-stock','legacy-build','legacy-v4'):
  assert len(prefix)==2 and c0['kind']==5 and c0['position']!=c0['next']
  retained=[c for c in movement(qend) if goal(c)==goal(c0)];assert len(retained)==1
  if case in ('reachable-stock-control','unreachable-stock'):
   own=one(q0['own_towns'],lambda t:t['position']==home)[1];s=own['recruit_state']
   assert s['owner']==1 and s['visitor'] is None and len(h0['army'])<7 and sum(raw.totals(s['upper_army']).values())==1
   assert any(c['kind']==4 and c['position']==home for c in movement(q0))==(case=='reachable-stock-control')
   expect=case=='reachable-stock-control' and plan['arm']=='candidate'
   assert len(movement(qend))==(2 if expect else 1)
   assert len([c for c in movement(qend) if c['kind']==4 and c['position']==home])==int(expect)
   with zipfile.ZipFile(f['path']) as z:g=json.loads(z.read('surface_terrain.json'))
   connected=land_connected(g,q0['from'],home);assert connected==(case=='reachable-stock-control')
   facts.update(native_owned_stock_positive=True,native_hero_has_empty_slot=True,precommit_town_candidate_present=case=='reachable-stock-control',ordinary_land_overapprox_connected=connected,post_commit_refill_exception=expect,town_no_path_log_claimed=False,scope='Native precommit candidate observation plus controlled owner/stock/capacity and verified terrain; no invented internal kind4 path-status record.')
  elif case=='nonowned-stock':
   assert not target(q0,home) and not target(qend,home)
   assert any(c['kind']==1 and c['position']==home for c in movement(q0)) and not any(c['kind']==4 and c['position']==home for c in movement(q0))
   assert len(movement(qend))==1
   path=work/'strategy-trace.jsonl.targets.jsonl';statuses=raw.lines(path)
   real=[r for r in statuses if r['day']==q0['day'] and r['hero']==q0['hero'] and r['from']==q0['from'] and r['kind']==1 and r['position']==home and r['status']=='candidate']
   assert real and all(r['tile_visible'] for r in real)
   facts.update(nonowned_town_reachable_kind1_observed=True,actual_kind1_path_audit=real,own_town_kind4_absent=True)
  else:
   assert q0['schema']==f['schema'] and any(c['kind']==4 and c['position']==home for c in movement(q0))
   assert len(movement(qend))==1 and goal(movement(qend)[0])==goal(c0)
   beforetown=one(q0['own_towns'],lambda t:t['position']==home)[1];aftertown=one(qend['own_towns'],lambda t:t['position']==home)[1]
   assert beforetown['army_value']>0 and aftertown['army_value']>0
   facts.update(original_schema=f['schema'],original_response_version=records[0]['response']['schema'],positive_town_stock_army_value_observed=True,own_town_path_candidate_before_commit=True,commitment_compression_move_count=1,scripted_legacy_economy_preserved=True,scripted_legacy_transaction_state_proof_claimed=False)
 elif case=='arrive-incompatible-stock':
  assert c0['kind']==4 and c0['position']==home and qend['from']==home
  assert len(initial_army)==7
  for q,c in prefix[:-1]:
   assert goal(c)==(home,4)
   if q is not q0:assert len(movement(q))==1
  before=one(q0['own_towns'],lambda t:t['position']==home)[1]['recruit_state'];after=one(qend['own_towns'],lambda t:t['position']==home)[1]['recruit_state']
  assert sum(raw.totals(before['upper_army']).values())==1 and raw.totals(before['upper_army'])==raw.totals(after['upper_army'])
  assert set(initial_army).isdisjoint(raw.totals(after['upper_army'])) and after['visitor']['hero_id']==q0['hero'] and raw.totals(after['visitor']['army'])==initial_army
  assert after['resources']==before['resources'] and raw.stock(after)==raw.stock(before) and result['actual_transfers_checked']==0
  assert not any(c['kind']==4 and c['position']==home for c in movement(qend)) and len(movement(qend))>1
  facts.update(real_arrival_at_positive_nonreceivable_stock=True,automatic_transfer_not_disabled=True,current_tile_zero_length_town_absent=True,old_town_commit_invalidated_by_arrival_without_stock_depletion=True,free_reselection_count=len(movement(qend)),receivable_positive_stock_at_policy_claimed=False)
 elif case=='consumed-pickup':
  assert c0['kind']==3 and c0['position']==[26,11,0]
  for q,c in prefix[:-1]:assert goal(c)==goal(c0)
  assert not any(goal(c)==goal(c0) for c in movement(qend)) and len(movement(qend))>1
  for resource in raw.RES:assert qend['resources'][resource]==q0['resources'][resource]+(800 if resource=='gold' else 0)
  assert result['actual_recruits_checked']==result['actual_transfers_checked']==0
  facts.update(original_pickup_consumed=True,exact_native_gold_gain=800,old_pickup_goal_absent=True,free_reselection_count=len(movement(qend)),hero_arrived_on_pickup_tile=qend['from']==c0['position'],invalidation_cause='Actual pickup consumption; do not infer entry into a blocking-visit tile.')
 else:raise AssertionError(case)
 result.update(schema='refill-boundary-independent-v1',case=case,arm=plan['arm'],boundary_facts=facts,actual_moves=moves_proven,mechanism_coverage_verified=True,new_native_games_by_auditor=0,optimizer_steps=0,strength_claim=False,model_promoted=False,final_test_used=False)
 result['raw_sha256'].update({str(p.relative_to(work)):sha(p) for p in [work/'agent/mechanism-selector.jsonl',work/'strategy-trace.jsonl',work/'NATIVE_LEASES.json',work/'agent/BROKER_LEASES.json']+list(work.glob('strategy-trace.jsonl.*')) if p.is_file()})
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 try:r=audit(a.raw)
 except BaseException as error:write(a.out/'AUDIT.json',dict(passed=False,error=repr(error),new_native_games=0,optimizer_steps=0));raise
 write(a.out/'AUDIT.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','raw_sha256','checks','drain')},indent=2))
if __name__=='__main__':main()
