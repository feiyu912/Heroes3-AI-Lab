"""Raw native contract plus independently checked refill retention coverage."""
import argparse,collections,json
from pathlib import Path
from common import HERE,CONTRACT,REGISTRY_SOURCE,load,sha,write,fixture,validate_capsule,verify_source_freeze
import raw_contract_auditor as raw

def only(rows,predicate):
 hits=[(i,r) for i,r in enumerate(rows) if predicate(r)];assert len(hits)==1,('Expected unique native evidence',len(hits));return hits[0]
def key(c):return (tuple(c['position']),c['kind'])
def moves(q):return [c for c in q['candidates'] if c['op']=='move']
def town(q,identity):return only(q['own_towns'],lambda t:t['town_id']==identity)[1]
def audit(work):
 verify_source_freeze()
 work=Path(work);plan=load(work/'PLAN.json');execution=load(work/'EXECUTION.json')
 validate_capsule(plan['capsule'],plan['arm']);manifest,f=fixture(plan['case'])
 assert plan['seed']==f['seed'] and plan['owned_player']==f['owned_player'] and plan['opponent']==f['opponent'] and plan['seconds']==f['max_seconds']
 assert plan['classification']=='diagnostic_only' and plan['training_samples']==plan['optimizer_steps']==0 and plan['checkpoint'] is None
 assert execution['passed'] is True and execution['owned_children_cleaned_before_release'] is True
 assert execution['native_inherited_fd_observations'] and len(execution['native_inherited_fd_observations'])==2
 for proof in [load(work/'NATIVE_LEASES.json'),load(work/'agent/BROKER_LEASES.json')]:
  assert proof['inherited_flock_verified'] is True and proof['entries']==plan['resource_locks']
 for actual,expected in zip(execution['native_inherited_fd_observations'],plan['resource_locks']):
  assert all(actual[k]==expected[k] for k in ['fd','device','inode'])
 result=raw.audit_game(work,HERE,mechanism=False)
 events=raw.lines(work/'typed.jsonl');records=raw.lines(work/'agent/mechanism-selector.jsonl');trace=raw.lines(work/'strategy-trace.jsonl')
 terminal_index,_=only(events,lambda e:e['event']=='game_over' and e.get('completed') is True and e['player']==plan['owned_player'])
 busy=[e for e in events[:terminal_index] if e['event']=='busy_state' and e['player']==plan['owned_player']]
 assert busy and busy[-1]['query_count']==0 and all(busy[-1][k] is False for k in ['movement_busy','economy_busy','battle_busy']),'Last actual busy snapshot has pending work at terminal'
 for index,event in enumerate(events):
  if event['event']=='native_action_sent' and event['player']==plan['owned_player']:
   previous=[e for e in events[:index] if e['event']=='busy_state' and e['player']==plan['owned_player']]
   assert previous and previous[-1]['query_count']==0 and all(previous[-1][k] is False for k in ['movement_busy','economy_busy','battle_busy']),'Action sent with actual busy/query work'
 assert records and len(records)==result['actual_decisions_checked']
 assert [r['request']['request_id'] for r in records]==list(range(1,len(records)+1))
 for i,r in enumerate(records,1):
  assert r['request']==load(work/f'agent/request-{i:08d}.json') and r['response']==load(work/f'agent/action-{i:08d}.json')
  assert r['response']['classification']=='diagnostic_only' and r['mechanism_only'] and not r['neural_network']
 selected=[(r['request'],r['request']['candidates'][r['response']['selected_index']],r) for r in records]
 prefix=[]
 for row in selected:
  prefix.append(row)
  if row[1]['op']=='end_turn':break
 assert prefix[-1][1]['op']=='end_turn'
 assert len({q['own_turn'] for q,c,r in prefix})==1 and len({q['hero'] for q,c,r in prefix})==1
 assert all(q['economy_window_open'] for q,c,r in prefix)
 for q,c,r in selected[len(prefix):]:assert c=={'op':'end_turn'},'Only EndTurn allowed after mechanism'
 assert not any((r.get('coverage_note') or '').startswith('uncovered:') for r in records),'Actual fixture precondition or candidate coverage failed'
 q0,c0,_=prefix[0];assert c0['op']=='move' and c0['kind']==5
 assert c0['position']!=c0['next'] and max(abs(a-b) for a,b in zip(c0['position'],q0['from']))>=4
 home=only(q0['own_towns'],lambda t:t['position']==q0['from'])[1];identity=home['town_id'];homepos=home['position'];initial=home['recruit_state']
 assert initial['owner']==q0['player'] and initial['visitor']['hero_id']==q0['hero'] and not any(initial['upper_army'])
 original=key(c0);initial_totals=raw.totals(initial['visitor']['army'])
 q1=prefix[1][0];assert q1['from']!=q0['from'] and q1['from']==c0['next'] and town(q1,identity)['recruit_state']['visitor'] is None
 assert len(moves(q1))==1 and key(moves(q1)[0])==original
 # Every selected move must produce a real received move result and a new
 # request at the actual candidate's next tile; no ACK-only coverage.
 move_checks=[]
 for idx,(q,c,r) in enumerate(prefix):
  if c['op']!='move':continue
  rid=q['request_id'];si,s=only(events,lambda e:e['event']=='native_action_sent' and e.get('decision_id')==rid)
  mi,m=only(events,lambda e:e['event']=='move_result' and e.get('decision_id')==rid)
  ai,a=only(events,lambda e:e['event']=='package_applied' and e.get('decision_id')==rid)
  assert si<mi<ai and m['source']=='server' and m['evidence']=='received_TryMoveHero' and m['native_request_id']==s['native_request_id']
  assert m['result']==1 and a['success'] is True and m['candidate']==c and m['request_sha256']==s['request_sha256']
  assert idx+1<len(prefix) and prefix[idx+1][0]['from']==c['next'] and c['next']!=q['from']
  # A real callback snapshot separately contains the hero's postmove location.
  snapshots=[t for t in trace if t['event']=='move_applied' and t['own_turn']==q['own_turn'] and any(h['id']==q['hero'] and [h['x'],h['y'],h['z']]==c['next'] for h in t['heroes'])]
  assert snapshots,'No actual postmove hero snapshot'
  move_checks.append(dict(decision_id=rid,native_request_id=s['native_request_id'],from_position=q['from'],to_position=c['next']))
 case=plan['case'];expect_refill=(plan['arm']=='candidate' and case in ('positive','full-merge'))
 if case=='empty':
  assert [c['op'] for q,c,r in prefix]==['move','end_turn']
  assert not any(town(q1,identity)['recruit_state']['upper_army'])
  assert len(moves(q1))==1 and result['actual_recruits_checked']==result['actual_transfers_checked']==0
 else:
  qrec,crec,_=prefix[1];assert crec['op']=='recruit' and crec['amount']==1 and crec['town_id']==identity
  assert crec['destination_army_id']==town(qrec,identity)['recruit_state']['upper_army_id'] and qrec['own_army_value']==q0['own_army_value']
  qpost=prefix[2][0];assert qpost['from']==qrec['from'] and qpost['own_army_value']==qrec['own_army_value']
  post=town(qpost,identity)['recruit_state'];assert raw.totals(post['upper_army'])=={crec['creature_id']:1} and post['visitor'] is None
  assert moves(qpost)[0]==moves(qrec)[0],'Old committed candidate fields changed while hero was stationary'
  if case.startswith('full-'):
   assert len([s for s in initial['visitor']['army'] if s])==7
   assert (crec['creature_id'] in initial_totals)==(case=='full-merge')
  if not expect_refill:
   assert [c['op'] for q,c,r in prefix]==['move','recruit','end_turn']
   assert len(moves(qpost))==1 and key(moves(qpost)[0])==original and result['actual_transfers_checked']==0
  else:
   assert len(prefix)>=5 and [c['op'] for q,c,r in prefix[:4]]==['move','recruit','move','move']
   assert len(moves(qpost))==2 and key(moves(qpost)[0])==original and key(moves(qpost)[1])==(tuple(homepos),4)
   assert prefix[2][1]==moves(qpost)[0],'Refill availability forced return instead of preserving old choice'
   qcontinue=prefix[3][0];assert len(moves(qcontinue))==2 and key(moves(qcontinue)[0])==original and key(moves(qcontinue)[1])==(tuple(homepos),4)
   for q,c,r in prefix[3:-1]:assert c['op']=='move' and key(c)==(tuple(homepos),4)
   qend=prefix[-1][0];endstate=town(qend,identity)['recruit_state']
   assert qend['from']==homepos and not any(endstate['upper_army']) and not any(c['kind']==4 and c['position']==homepos for c in moves(qend))
   expected=dict(initial_totals);expected[crec['creature_id']]=expected.get(crec['creature_id'],0)+1
   assert raw.totals(endstate['visitor']['army'])==expected
   assert endstate['resources']==post['resources'] and raw.stock(endstate)==raw.stock(post)
   transfers=[e for e in events if e['event']=='free_transfer_native_sent'];assert len(transfers)==1
   sent=transfers[0];assert sent['creature_id']==crec['creature_id'] and sent['amount']==1 and sent['source_army_id']==crec['destination_army_id'] and sent['target_army_id']==q0['hero']
   if case=='full-merge':assert sent['actual_what']==2
   _,recruit_ack=only(events,lambda e:e['event']=='recruit_ack_state' and e.get('decision_id')==qrec['request_id'])
   transfer_index,_=only(events,lambda e:e['event']=='free_transfer_native_sent')
   recruit_index,_=only(events,lambda e:e is recruit_ack)
   end_index,_=only(events,lambda e:e['event']=='native_action_sent' and e.get('decision_id')==qend['request_id'])
   _,ack=only(events,lambda e:e['event']=='free_transfer_ack_state' and e['native_request_id']==sent['native_request_id'])
   ack_index,_=only(events,lambda e:e is ack)
   assert recruit_index<transfer_index<ack_index<end_index
   assert ack['state_change_verified'] is True and ack['success'] is True
 result.update(schema='refill-retention-independent-audit-v1',arm=plan['arm'],case=case,mechanism_coverage_verified=True,refill_expected=expect_refill,refill_coverage_verified=expect_refill,continued_original_commit_before_refill=expect_refill,move_checks=move_checks,whole_game_valid=True,one_turn_sequence=[c['op'] for q,c,r in prefix],strength_claim=False,model_promoted=False,final_test_used=False)
 result['raw_sha256'].update({str(p.relative_to(work)):sha(p) for p in [work/'agent/mechanism-selector.jsonl',work/'agent/BROKER_LEASES.json',work/'NATIVE_LEASES.json',work/'LEASES.json',work/'strategy-trace.jsonl']})
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 try:result=audit(a.raw)
 except BaseException as error:
  write(a.out/'AUDIT.json',dict(passed=False,error=repr(error),raw=str(a.raw),native_runs_by_auditor=0,optimizer_steps=0));raise
 write(a.out/'AUDIT.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ('raw_sha256','source_sha256','checks','drain')},indent=2))
if __name__=='__main__':main()
