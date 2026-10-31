"""Same deterministic actual-candidate selector for both arms. No NN or teacher."""
import argparse,hashlib,json,os,time
from pathlib import Path
from common import leases,write
TOP=set('schema request_id player own_turn own_hero_count day hero from gold wood ore own_army_value movement visible_threats economy_epoch economy_window_open resources creature_catalog_sha256 own_towns candidates'.split())
RES=set('wood mercury ore sulfur crystal gems gold'.split())
def digest(b):return hashlib.sha256(b).hexdigest()
def atomic(p,b):
 tmp=p.with_name(p.name+'.tmp')
 with tmp.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def catalog(folder,q):
 raw=(folder/'creature-catalog.json').read_bytes();d=json.loads(raw)
 assert raw.endswith(b'\n') and digest(raw)==q['creature_catalog_sha256']
 assert set(d)=={'schema','entries'} and d['schema']=='strategy-runtime-creature-catalog-v1' and d['entries']
 ids=[x['creature_id'] for x in d['entries']];keys=[x['canonical_key'] for x in d['entries']]
 assert ids==sorted(set(ids)) and len(keys)==len(set(keys)) and all(type(i)is int and i>=0 for i in ids)
 assert all(set(x)=={'creature_id','canonical_key'} and isinstance(x['canonical_key'],str) and x['canonical_key'] for x in d['entries'])
 for town in q['own_towns']:
  for stock in town['recruit_state']['recruit_stock']:assert set(stock['creature_ids'])<=set(ids)
 return d
class Selector:
 def __init__(self,case):
  self.case=case;self.phase='commit';self.turn=None;self.home=None;self.homepos=None;self.goal=None;self.creature=None;self.reason=None;self.initial_army=None
 def select(self,q):
  assert set(q)==TOP and q['schema']=='strategy-candidates-v6' and q['economy_epoch']=='learned-economy-build-recruit-v1'
  assert q['own_hero_count']==1 and type(q['hero'])is int and q['hero']>=0 and set(q['resources'])==RES
  cs=q['candidates'];ends=[i for i,c in enumerate(cs) if c=={'op':'end_turn'}];assert len(ends)==1
  end=ends[0]
  if self.phase=='done':return end
  if self.turn is None:
   self.turn=q['own_turn'];homes=[t for t in q['own_towns'] if t['position']==q['from']]
   if len(homes)!=1:return self.fail('no_unique_initial_visitor_town',end)
   t=homes[0];s=t['recruit_state'];v=s['visitor']
   if not v or v['hero_id']!=q['hero'] or any(s['upper_army']):return self.fail('initial_town_not_empty_or_hero_not_visitor',end)
   self.home=t['town_id'];self.homepos=t['position'];self.initial_army=v['army']
  if q['own_turn']!=self.turn or not q['economy_window_open']:return self.fail('sequence_not_one_open_own_turn',end)
  towns=[t for t in q['own_towns'] if t['town_id']==self.home]
  if len(towns)!=1:return self.fail('home_lost',end)
  town=towns[0];moves=[(i,c) for i,c in enumerate(cs) if c['op']=='move']
  committed=[(i,c) for i,c in moves if self.goal and (c['position'],c['kind'])==self.goal]
  refill=[(i,c) for i,c in moves if c['kind']==4 and c['position']==self.homepos]
  if self.phase=='commit':
   possible=[(i,c) for i,c in moves if c['kind']==5 and c['position']!=c['next'] and max(abs(a-b) for a,b in zip(c['position'],q['from']))>=4 and c['next']!=self.homepos]
   possible.sort(key=lambda pair:(-pair[1]['path_cost'],pair[1]['position'],pair[0]))
   if not possible:return self.fail('no_actual_far_frontier_goal',end)
   i,c=possible[0];self.goal=(c['position'],c['kind']);self.phase='inspect_empty' if self.case=='empty' else 'recruit';return i
  if self.phase in ('recruit','inspect_empty'):
   if q['from']==self.homepos or town['recruit_state']['visitor'] is not None:return self.fail('first_move_did_not_leave_town',end)
   if len(committed)!=1:return self.fail('old_frontier_no_longer_admissible',end)
   if len(moves)!=1 or refill:return self.fail('empty_home_has_unexpected_movement_exception',end)
   if self.case=='empty':self.phase='done';self.reason='empty_boundary_observed';return end
   choices=[(i,c) for i,c in enumerate(cs) if c['op']=='recruit' and c['town_id']==self.home and c['amount']==1]
   choices.sort(key=lambda pair:(pair[1]['creature_id'],pair[1]['level'],pair[1]['destination_army_id']))
   if not choices:return self.fail('no_actual_remote_amount1_recruit',end)
   i,c=choices[0];self.creature=c['creature_id'];self.phase='inspect_refill';return i
  if self.phase=='inspect_refill':
   if len(committed)!=1:return self.fail('old_commit_missing_after_recruit',end)
   if not refill:
    if len(moves)!=1:return self.fail('unrelated_moves_after_commit',end)
    self.phase='done';self.reason='refill_absent_after_real_remote_recruit';return end
   if len(refill)!=1 or len(moves)!=2:return self.fail('duplicate_or_unrelated_move_exception',end)
   self.phase='choose_refill';return committed[0][0]
  if self.phase=='choose_refill':
   if len(committed)!=1 or len(refill)!=1 or len(moves)!=2:return self.fail('original_commit_or_refill_not_retained_after_continuing',end)
   self.phase='return';return refill[0][0]
  if self.phase=='return':
   if q['from']==self.homepos:
    if refill:return self.fail('zero_distance_refill_candidate',end)
    if any(town['recruit_state']['upper_army']):return self.fail('stock_not_fully_transferred_before_policy',end)
    self.phase='done';self.reason='returned_and_stock_empty';return end
   if len(refill)!=1:return self.fail('refill_path_lost_before_town',end)
   return refill[0][0]
  raise AssertionError(self.phase)
 def fail(self,reason,end):self.phase='done';self.reason='uncovered:'+reason;return end

def main():
 p=argparse.ArgumentParser();p.add_argument('--agent-dir',type=Path,required=True);p.add_argument('--case',choices=['positive','empty','full-incompatible','full-merge'],required=True);p.add_argument('--idle-seconds',type=float,default=210);a=p.parse_args()
 proof=leases.verify_pair();a.agent_dir.mkdir(exist_ok=True,parents=True);write(a.agent_dir/'BROKER_LEASES.json',proof)
 atomic(a.agent_dir/'broker-ready.json',json.dumps(dict(mode='refill-retention-mechanism-only',device='cpu',neural_network=False,training_samples=0,optimizer_steps=0,lease_verified=True)).encode()+b'\n')
 selector=Selector(a.case);number=1;last=time.monotonic()
 while True:
  path=a.agent_dir/f'request-{number:08d}.json'
  if not path.exists():
   if time.monotonic()-last>a.idle_seconds:raise TimeoutError('No native request; never fabricate one')
   time.sleep(.01);continue
  raw=path.read_bytes();q=json.loads(raw);assert q['request_id']==number;catalog(a.agent_dir,q)
  phase=selector.phase;index=selector.select(q)
  response=dict(schema='strategy-typed-action-response-v3',selected_index=index,decision_id=number,player=q['player'],hero=q['hero'],own_turn=q['own_turn'],op=q['candidates'][index]['op'],request_sha256=digest(raw),classification='diagnostic_only')
  record=dict(request=q,response=response,mechanism_only=True,neural_network=False,phase_before=phase,phase_after=selector.phase,coverage_note=selector.reason,home=selector.home,home_position=selector.homepos,original_goal=selector.goal)
  with (a.agent_dir/'mechanism-selector.jsonl').open('a') as stream:stream.write(json.dumps(record,separators=(',',':'))+'\n');stream.flush();os.fsync(stream.fileno())
  atomic(a.agent_dir/f'action-{number:08d}.json',json.dumps(response,separators=(',',':')).encode()+b'\n');number+=1;last=time.monotonic()
if __name__=='__main__':main()
