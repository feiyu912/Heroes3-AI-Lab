"""Deterministic boundary selections from actual candidates, never a teacher."""
import argparse,json,os,time
from pathlib import Path
from boundary_common import HERE,fixture,leases,write,old_selector
prior=old_selector();atomic=prior.atomic;digest=prior.digest
class Selector:
 def __init__(self,case):self.case=case;self.phase='start';self.turn=None;self.goal=None;self.note=None;self.home=[29,8,0]
 def fail(self,reason,end):self.phase='done';self.note='uncovered:'+reason;return end
 def select(self,q):
  _,f=fixture(self.case);assert q['schema']==f['schema'] and q['own_hero_count']==1 and q['player']==1
  expected=prior.TOP if f['schema']=='strategy-candidates-v6' else prior.TOP-{'creature_catalog_sha256'} if f['schema']=='strategy-candidates-v5' else prior.TOP-{'creature_catalog_sha256','economy_epoch','economy_window_open','resources'}
  assert set(q)==expected
  cs=q['candidates'];ends=[i for i,c in enumerate(cs) if c=={'op':'end_turn'}];assert len(ends)==1;end=ends[0]
  if self.phase=='done':return end
  if self.turn is None:self.turn=q['own_turn']
  if q['own_turn']!=self.turn:return self.fail('sequence_crossed_own_turn',end)
  ms=[(i,c) for i,c in enumerate(cs) if c['op']=='move']
  if self.phase=='start':
   if q['from']!=f['expected_initial_hero_position']:return self.fail('wrong_initial_native_position',end)
   if self.case=='arrive-incompatible-stock':choices=[(i,c) for i,c in ms if c['kind']==4 and c['position']==self.home]
   elif self.case=='consumed-pickup':choices=[(i,c) for i,c in ms if c['kind']==3 and c['position']==[26,11,0]]
   else:
    choices=[(i,c) for i,c in ms if c['kind']==5 and max(abs(a-b) for a,b in zip(c['position'],q['from']))>=4 and c['position']!=c['next']]
    choices.sort(key=lambda pair:(-pair[1]['path_cost'],pair[1]['position'],pair[0]))
   if not choices:return self.fail('no_registered_actual_initial_goal',end)
   i,c=choices[0];self.goal=(c['position'],c['kind']);self.phase='follow' if self.case in ('arrive-incompatible-stock','consumed-pickup') else 'inspect';return i
  retained=[(i,c) for i,c in ms if (c['position'],c['kind'])==self.goal]
  if self.phase=='inspect':
   if len(retained)!=1:return self.fail('frontier_commit_no_longer_admissible',end)
   self.phase='done';self.note='post_commit_observed';return end
  if self.phase=='follow':
   if retained:
    if len(retained)!=1:return self.fail('duplicate_old_goal',end)
    return retained[0][0]
   if self.case=='arrive-incompatible-stock' and q['from']!=self.home:return self.fail('town_goal_disappeared_before_arrival',end)
   if not ms:return self.fail('no_free_reselection_after_old_goal_disappeared',end)
   self.phase='done';self.note='old_goal_absent_and_free_reselection';return end
  raise AssertionError(self.phase)
def main():
 p=argparse.ArgumentParser();p.add_argument('--agent-dir',type=Path,required=True);p.add_argument('--case',required=True);p.add_argument('--idle-seconds',type=float,default=210);a=p.parse_args();fixture(a.case)
 proof=leases.verify_pair();a.agent_dir.mkdir(exist_ok=True,parents=True);write(a.agent_dir/'BROKER_LEASES.json',proof)
 atomic(a.agent_dir/'broker-ready.json',json.dumps(dict(mode='refill-boundary-only',device='cpu',neural_network=False,training_samples=0,optimizer_steps=0,lease_verified=True)).encode()+b'\n')
 selector=Selector(a.case);number=1;last=time.monotonic()
 while True:
  path=a.agent_dir/f'request-{number:08d}.json'
  if not path.exists():
   if time.monotonic()-last>a.idle_seconds:raise TimeoutError('No native request')
   time.sleep(.01);continue
  data=path.read_bytes();q=json.loads(data);assert q['request_id']==number
  if q['schema']=='strategy-candidates-v6':prior.catalog(a.agent_dir,q)
  before=selector.phase;i=selector.select(q);response_schema={'strategy-candidates-v4':'strategy-typed-action-response-v1','strategy-candidates-v5':'strategy-typed-action-response-v2','strategy-candidates-v6':'strategy-typed-action-response-v3'}[q['schema']]
  response=dict(schema=response_schema,selected_index=i,decision_id=number,player=q['player'],hero=q['hero'],own_turn=q['own_turn'],op=q['candidates'][i]['op'],request_sha256=digest(data),classification='diagnostic_only')
  record=dict(request=q,response=response,phase_before=before,phase_after=selector.phase,coverage_note=selector.note,original_goal=selector.goal,mechanism_only=True,neural_network=False)
  with (a.agent_dir/'mechanism-selector.jsonl').open('a') as stream:stream.write(json.dumps(record,separators=(',',':'))+'\n');stream.flush();os.fsync(stream.fileno())
  atomic(a.agent_dir/f'action-{number:08d}.json',json.dumps(response,separators=(',',':')).encode()+b'\n');number+=1;last=time.monotonic()
if __name__=='__main__':main()
