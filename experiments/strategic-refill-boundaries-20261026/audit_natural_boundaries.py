"""Re-audit two existing native games; derive narrow natural boundary facts."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parent.parent
V1=HERE.parent/'strategic-refill-retention-qualification-20261025'
sys.path.insert(0,str(V1))
import audit_mechanism as prior
from common import load,sha,write,verify_source_freeze
import raw_contract_auditor as raw
BASE=HERE.parent/'strategic-refill-paired-build-20261026/native-01'
def one(rows,check):
 hits=[(i,r) for i,r in enumerate(rows) if check(r)];assert len(hits)==1,len(hits);return hits[0]
def selected(r):return r['request']['candidates'][r['response']['selected_index']]
def moves(q):return [c for c in q['candidates'] if c['op']=='move']
def audit(folder):
 verified=prior.audit(folder)
 records=raw.lines(folder/'agent/mechanism-selector.jsonl');events=raw.lines(folder/'typed.jsonl')
 home=records[0]['request']['from'];hero=records[0]['request']['hero']
 first_return_index,first_return=next((i,r) for i,r in enumerate(records) if selected(r)['op']=='move' and selected(r)['kind']==4 and selected(r)['position']==home)
 continuation=records[first_return_index+1];q=continuation['request'];cs=moves(q)
 assert q['own_turn']==first_return['request']['own_turn'] and q['from']!=home
 assert len(cs)==1 and cs[0]['kind']==4 and cs[0]['position']==home and selected(continuation)==cs[0]
 state=one(q['own_towns'],lambda t:t['position']==home)[1]['recruit_state'];assert sum(raw.totals(state['upper_army']).values())==1 and state['visitor'] is None
 rid=q['request_id'];move_i,m=one(events,lambda e:e['event']=='move_result' and e.get('decision_id')==rid)
 assert m['result']==1 and m['candidate']['next']==home
 sent_i,s=one(events,lambda e:e['event']=='free_transfer_native_sent');ack_i,a=one(events,lambda e:e['event']=='free_transfer_ack_state' and e['native_request_id']==s['native_request_id'])
 assert move_i<sent_i<ack_i and s['before_state']==a['before_state']
 before=s['before_state'];assert before['visitor']['hero_id']==hero and sum(raw.totals(before['upper_army']).values())==1
 raw.transfer_state(s,before,a['state']);assert a['state_change_verified'] and not raw.totals(a['state']['upper_army'])
 arrive=records[first_return_index+2];aq=arrive['request']
 assert aq['from']==home and aq['own_turn']==q['own_turn'] and selected(arrive)=={'op':'end_turn'}
 assert not any(c['kind']==4 and c['position']==home for c in moves(aq)) and len(moves(aq))>1
 snapshot=one(aq['own_towns'],lambda t:t['position']==home)[1]['recruit_state']
 assert snapshot==a['state']
 return dict(raw=str(folder),existing_game_reaudited=True,whole_native_contract_passed=verified['passed'],actual_whole_terminal_and_drain=True,
  deduplicated_committed_town=dict(covered=True,initial_return_decision_id=first_return['request']['request_id'],continuation_decision_id=rid,continuation_position=q['from'],town_position=home,actual_move_count=len(cs),stock_positive_at_continuation=True,real_arrival_move_request_id=m['native_request_id']),
  current_tile_after_transfer=dict(covered=True,transfer_request_id=s['native_request_id'],positive_stock_and_real_visitor_before_transfer=True,full_transfer_conservation_verified=True,next_policy_request_id=aq['request_id'],town_stock_empty_at_policy=True,zero_length_town_candidate_absent=True),
  invalidated_town_commit_after_arrival_and_depletion=dict(covered=True,same_own_turn=True,old_goal_absent=True,free_movement_choices=len(moves(aq)),limitation='Arrival at current tile and stock depletion co-occur; these two causes are not separately identified.'),
  receivable_positive_stock_at_current_tile_policy=dict(covered=False,reason='Existing automatic transfer executes before the next policy request. Positive stock is observed only in the real pre-transfer transaction state; no policy observation with positive receivable stock was exposed.'),
  raw_sha256={str(p.relative_to(folder)):sha(p) for p in [folder/'PLAN.json',folder/'EXECUTION.json',folder/'typed.jsonl',folder/'client.log',folder/'strategy-trace.jsonl',folder/'agent/mechanism-selector.jsonl']+sorted((folder/'agent').glob('request-*.json'))+sorted((folder/'agent').glob('action-*.json'))})
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 result=dict(passed=False,new_native_games=0,GPU_runs=0,optimizer_steps=0,final_test_used=False,strength_claim=False)
 try:
  verify_source_freeze();result['games']=[audit(BASE/name) for name in ['candidate-positive','candidate-full-merge']];result['passed']=True
  result['auditor_source_sha256']={str(p):sha(p) for p in [Path(__file__),V1/'SOURCE_FREEZE.json',V1/'audit_mechanism.py',V1/'raw_contract_auditor.py',V1/'common.py']}
 except BaseException as error:result['error']=repr(error);raise
 finally:write(a.out/'AUDIT.json',result)
 print(json.dumps({k:v for k,v in result.items() if k!='games'},indent=2))
if __name__=='__main__':main()
