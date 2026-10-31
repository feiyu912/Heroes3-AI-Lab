"""Actual-candidate deterministic mechanism selector; no NN/torch/sampling/PPO."""
import argparse,hashlib,json,os,time
from pathlib import Path
TOP=set('schema request_id player own_turn own_hero_count day hero from gold wood ore own_army_value movement visible_threats economy_epoch economy_window_open resources creature_catalog_sha256 own_towns candidates'.split())
RES=['wood','mercury','ore','sulfur','crystal','gems','gold']
def digest(b):return hashlib.sha256(b).hexdigest()
def atomic(p,b):
 tmp=p.with_name(p.name+'.tmp')
 with tmp.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 os.replace(tmp,p)
def catalog(folder,q):
 b=(folder/'creature-catalog.json').read_bytes();assert b.endswith(b'\n') and digest(b)==q['creature_catalog_sha256']
 d=json.loads(b);assert set(d)=={'schema','entries'} and d['schema']=='strategy-runtime-creature-catalog-v1' and d['entries']
 ids=[e['creature_id'] for e in d['entries']];keys=[e['canonical_key'] for e in d['entries']]
 assert ids==sorted(set(ids)) and len(keys)==len(set(keys)) and all(type(i)is int and i>=0 for i in ids)
 assert all(set(e)=={'creature_id','canonical_key'} and isinstance(e['canonical_key'],str) and e['canonical_key'] for e in d['entries'])
 for town in q['own_towns']:
  for stock in town['recruit_state']['recruit_stock']:assert set(stock['creature_ids'])<=set(ids)
 return d
class Selector:
 def __init__(self):self.phase='build';self.turn=None;self.home=None;self.position=None;self.creature=None;self.coverage_incomplete=None
 def select(self,q):
  assert set(q)==TOP and q['schema']=='strategy-candidates-v6' and q['economy_epoch']=='learned-economy-build-recruit-v1'
  assert q['own_hero_count']==1 and type(q['hero'])is int and q['hero']>=0 and set(q['resources'])==set(RES)
  cs=q['candidates'];assert cs
  ends=[i for i,c in enumerate(cs) if c=={'op':'end_turn'}];assert len(ends)==1
  if self.phase=='done' or self.coverage_incomplete:return ends[0]
  if self.turn is None:
   self.turn=q['own_turn'];homes=[t for t in q['own_towns'] if t['position']==q['from']]
   if len(homes)!=1:self.coverage_incomplete='no_unique_initial_town';return ends[0]
   self.home=homes[0]['town_id'];self.position=homes[0]['position']
  if q['own_turn']!=self.turn or not q['economy_window_open']:
   self.coverage_incomplete='sequence_did_not_remain_in_one_open_own_turn';return ends[0]
  choices=[]
  if self.phase=='build':
   choices=[i for i,c in enumerate(cs) if c['op']=='build' and c['town_id']==self.home]
   choices.sort(key=lambda i:tuple(cs[i]['cost'][r] for r in ['gold','wood','ore','mercury','sulfur','crystal','gems'])+(cs[i]['building_id'],))
   nextphase='recruit_first'
  elif self.phase in ['recruit_first','recruit_same']:
   choices=[i for i,c in enumerate(cs) if c['op']=='recruit' and c['town_id']==self.home and c['amount']==1 and (self.creature is None or c['creature_id']==self.creature) and (self.creature is not None or c['available']>=2)]
   choices.sort(key=lambda i:(cs[i]['creature_id'],cs[i]['level'],cs[i]['destination_army_id']))
   nextphase='move_out' if self.phase=='recruit_first' else 'return'
  elif self.phase=='move_out':
   choices=[i for i,c in enumerate(cs) if c['op']=='move' and c['kind']==3 and c['position']==c['next'] and c['next']!=q['from'] and sum(abs(c['next'][j]-q['from'][j]) for j in range(3))==1]
   choices.sort(key=lambda i:(cs[i]['path_cost'],cs[i]['position'],i));nextphase='recruit_same'
  elif self.phase=='return':
   if q['from']==self.position:self.phase='done';return ends[0] # Actual resource visit may leave the hero on its entry tile.
   choices=[i for i,c in enumerate(cs) if c['op']=='move' and c['kind']==4 and c['position']==self.position]
   choices.sort(key=lambda i:(cs[i]['path_cost'],i));nextphase='confirm_return'
  elif self.phase=='confirm_return':
   if q['from']!=self.position:self.coverage_incomplete='return_did_not_reach_town';return ends[0]
   self.phase='done';return ends[0]
  else:raise AssertionError(self.phase)
  if not choices:self.coverage_incomplete='missing_actual_legal_candidate_at_'+self.phase;return ends[0]
  index=choices[0]
  if self.phase=='recruit_first':self.creature=cs[index]['creature_id']
  self.phase=nextphase;return index
def main():
 p=argparse.ArgumentParser();p.add_argument('--agent-dir',type=Path,required=True);p.add_argument('--idle-seconds',type=float,default=270);a=p.parse_args();a.agent_dir.mkdir(exist_ok=True,parents=True)
 # Native init exports catalog only AFTER runner launches client. Publish ready first.
 atomic(a.agent_dir/'broker-ready.json',json.dumps(dict(mode='schema6-mechanism-only',device='cpu',neural_network=False,training_samples=0,optimizer_steps=0)).encode()+b'\n')
 selector=Selector();number=1;last=time.monotonic()
 while True:
  path=a.agent_dir/f'request-{number:08d}.json'
  if not path.exists():
   if time.monotonic()-last>a.idle_seconds:raise TimeoutError('Mechanism selector idle; no fabricated response')
   time.sleep(.01);continue
  raw=path.read_bytes();q=json.loads(raw);assert q['request_id']==number;catalog(a.agent_dir,q)
  before=selector.phase;index=selector.select(q)
  response=dict(schema='strategy-typed-action-response-v3',selected_index=index,decision_id=number,player=q['player'],hero=q['hero'],own_turn=q['own_turn'],op=q['candidates'][index]['op'],request_sha256=digest(raw),classification='diagnostic_only')
  record=dict(request=q,response=response,mechanism_only=True,neural_network=False,phase_before=before,phase_after=selector.phase,coverage_incomplete=selector.coverage_incomplete)
  with (a.agent_dir/'mechanism-selector.jsonl').open('a') as f:f.write(json.dumps(record,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())
  atomic(a.agent_dir/f'action-{number:08d}.json',json.dumps(response,separators=(',',':')).encode()+b'\n');number+=1;last=time.monotonic()
if __name__=='__main__':main()
