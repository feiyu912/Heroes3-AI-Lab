"""Independent schema6 raw auditor. Never invokes native/torch/optimizer."""
import argparse,collections,hashlib,json,re,importlib.util
from pathlib import Path
RES=set('wood mercury ore sulfur crystal gems gold'.split())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def lines(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def totals(army):
 assert len(army)==7
 out=collections.Counter()
 for slot,s in enumerate(army):
  if s is not None:
   assert s['slot']==slot and s['count']>0 and s['creature_id']>=0
   out[s['creature_id']]+=s['count']
 return out
def visitor_identity(s):return None if s['visitor'] is None else {k:v for k,v in s['visitor'].items() if k!='army'}
def stock(s):
 a={e['level']:e for e in s['recruit_stock']};assert len(a)==len(s['recruit_stock']);return a
def base_state(b,a):
 assert set(b['resources'])==set(a['resources'])==RES
 for k in ['town_id','owner','upper_army_id','built_today']:assert b[k]==a[k],k
 assert visitor_identity(b)==visitor_identity(a)
def delta(before,after,creature,amount):
 expected=dict(before);expected[creature]=expected.get(creature,0)+amount
 assert all(v>=0 for v in expected.values())
 assert {k:v for k,v in expected.items() if v}==dict(after)
def recruit_state(c,b,a):
 base_state(b,a);assert b['upper_army_id']==c['destination_army_id']
 assert c['amount']>0 and c['amount']<=min(c['available'],c['affordable']) and c['destination_slot'] in range(7)
 for r in RES:assert a['resources'][r]==b['resources'][r]-c['cost'][r]
 sb,sa=stock(b),stock(a);assert sb.keys()==sa.keys()
 for level in sb:
  assert sb[level]['creature_ids']==sa[level]['creature_ids']
  assert sa[level]['available']==sb[level]['available']-(c['amount'] if level==c['level'] else 0)
 assert c['creature_id'] in sb[c['level']]['creature_ids']
 assert sb[c['level']]['available']==c['available']
 delta(totals(b['upper_army']),totals(a['upper_army']),c['creature_id'],c['amount'])
 if b['visitor'] is not None and b['visitor']['army_id']!=b['upper_army_id']:
  assert totals(b['visitor']['army'])==totals(a['visitor']['army'])
def transfer_state(sent,b,a):
 base_state(b,a);assert b['resources']==a['resources'] and stock(b)==stock(a)
 assert b['visitor'] is not None
 assert sent['source_army_id']==b['upper_army_id'] and sent['target_army_id']==b['visitor']['army_id']
 original=b['upper_army'][sent['from_slot']]
 assert original and original['creature_id']==sent['creature_id'] and original['count']==sent['amount']
 assert sent['actual_val']==0 and sent['actual_what'] in [1,2]
 delta(totals(b['upper_army']),totals(a['upper_army']),sent['creature_id'],-sent['amount'])
 delta(totals(b['visitor']['army']),totals(a['visitor']['army']),sent['creature_id'],sent['amount'])
def log_records(log,tag):
 records=[]
 for i,line in enumerate(log.splitlines()):
  if tag+' ' not in line:continue
  d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
  # Native ui8 is formatted as its raw byte by boost log, not decimal.
  what=re.search(r' what=([\x01\x02\x03]) val=',line)
  if what:d['what']=ord(what[1])
  records.append((d,i))
 return records
def unique(rows,predicate):
 hits=[(i,r) for i,r in enumerate(rows) if predicate(r)];assert len(hits)==1,('expected unique',len(hits));return hits[0]
def audit_game(work,native,mechanism=False):
 work=Path(work);native=Path(native)
 plan=load(work/'PLAN.json');execution=load(work/'EXECUTION.json');events=lines(work/'typed.jsonl');log=(work/'client.log').read_text(errors='replace')
 if mechanism:
  assert plan['classification']=='diagnostic_only' and plan['training_samples']==plan['optimizer_steps']==0
  assert plan['owned_player']==1 and plan['opponent']=='Nullkiller2' and plan['seed']==2026103501
 assert execution['game_completed'] and execution['transport_drained'] and execution['client_exit']==0 and execution['input_sha_unchanged']
 assert execution['thread_server_verification']['passed']
 for path,h in plan['hashes'].items():assert sha(Path(path))==h,path
 assert not any(e['event']=='typed_protocol_error' for e in events)
 mirrored=[json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ',1)[1])[0] for line in log.splitlines() if 'DirectorTypedEvent ' in line]
 assert mirrored==events,'typed sidecar differs from actual client log mirror'
 registry_path=Path('/mnt/g/Heroes3-AI-Lab/experiments/strategic-director-terminal-drain-v4/director_registry_v1.py')
 spec=importlib.util.spec_from_file_location('_independent_registry',registry_path);registry=importlib.util.module_from_spec(spec);spec.loader.exec_module(registry)
 assert str(registry_path) in plan['hashes'],'registry must be frozen source input'
 drain=registry.verify(log,plan['owned_player'])
 assert any(e['event']=='game_over' and e.get('completed') is True for e in events)
 capsule=Path(plan['capsule']);att=load(capsule/'EXECUTION.json');manifest=load(capsule/'build-source-manifest.json')
 assert att['passed'] and att['accepted_binaries_restored'] and att['accepted_sources_restored'] and not att['rebuild_required']
 for path,h in att['candidate_artifacts'].items():assert sha(capsule/path)==h
 observed=execution['loaded_library_observations'];assert observed and all(e['valid'] for e in observed)
 assert any(e.get('libraries') for e in observed)
 for o in observed:
  assert o['executable_sha256']==sha(capsule/'bin/vcmiclient') and o['executable_matches_capsule']
  assert Path(o['executable']).resolve()==(capsule/'bin/vcmiclient').resolve()
  for lib in o['libraries']:
   assert lib['inode_matches'] and lib['device_matches'] and lib['path_matches'] and lib['sha256']==lib['expected_sha256']
   assert not lib['deleted'] and lib['sha256']==sha(capsule/'bin/libvcmi.so')
   assert Path(lib['path']).resolve()==Path(lib['expected_path']).resolve()==(capsule/'bin/libvcmi.so').resolve()
 # Independently bind source closure to the source manifest frozen by collector.
 n=native;m=load(n/'CANDIDATE_MANIFEST.json')
 for p in [n/'CANDIDATE_MANIFEST.json',n/'CONTRACT.md',capsule/'build-source-manifest.json',capsule/'EXECUTION.json']:
  assert str(p) in plan['hashes'] and sha(p)==plan['hashes'][str(p)],str(p)
 assert sha(n/'CONTRACT.md')==m['contract_sha256']==att['flow_contract_sha256']
 assert sha(n/'CANDIDATE_MANIFEST.json')==att['candidate_manifest_sha256']
 for path,e in m['files'].items():assert sha(n/'candidate'/path)==sha(capsule/'source-snapshot'/path)==manifest[path]['sha256']==e['candidate_sha256']
 catpath=work/'agent/creature-catalog.json';cat=load(catpath);catsha=sha(catpath);raw=catpath.read_bytes();assert raw.endswith(b'\n')
 assert set(cat)=={'schema','entries'} and cat['schema']=='strategy-runtime-creature-catalog-v1' and cat['entries']
 ids=[e['creature_id'] for e in cat['entries']];keys=[e['canonical_key'] for e in cat['entries']]
 assert all(set(e)=={'creature_id','canonical_key'} for e in cat['entries'])
 assert ids==sorted(set(ids)) and len(keys)==len(set(keys)) and all(type(i)is int and i>=0 for i in ids) and all(isinstance(k,str) and k for k in keys)
 mirrors=[line.split('DirectorCreatureCatalog ',1)[1] for line in log.splitlines() if 'DirectorCreatureCatalog ' in line]
 assert len(mirrors)==1 and mirrors[0]=='sha256='+catsha+' json='+raw[:-1].decode()
 if mechanism:records=lines(work/'agent/mechanism-selector.jsonl')
 else:
  records=[]
  for p in sorted((work/'agent').glob('request-*.json')):
   q=load(p);response=load(work/'agent'/f"action-{q['request_id']:08d}.json")
   records.append(dict(request=q,response=response))
 assert records
 selected=[];checks=[]
 for record in records:
  q=record['request'];response=record['response'];rid=q['request_id'];reqpath=work/'agent'/f'request-{rid:08d}.json';actpath=work/'agent'/f'action-{rid:08d}.json'
  assert load(reqpath)==q and load(actpath)==response and sha(reqpath)==response['request_sha256']
  assert q['schema']=='strategy-candidates-v6' and q['economy_epoch']=='learned-economy-build-recruit-v1' and q['player']==plan['owned_player']
  assert response['schema']=='strategy-typed-action-response-v3' and response['decision_id']==rid and response['player']==q['player'] and response['hero']==q['hero'] and response['own_turn']==q['own_turn']
  assert q['creature_catalog_sha256']==catsha
  if mechanism:
   assert response['classification']=='diagnostic_only' and record['mechanism_only'] and not record['neural_network'] and record['coverage_incomplete'] is None
  c=q['candidates'][response['selected_index']];assert c['op']==response['op'];selected.append((q,c,record))
  si,s=unique(events,lambda e:e['event']=='native_action_sent' and e.get('decision_id')==rid)
  ai,a=unique(events,lambda e:e['event']=='package_applied' and e.get('decision_id')==rid)
  for e in [s,a]:
   assert e['request_sha256']==sha(reqpath) and e['candidate']==c and e['selected_index']==response['selected_index'] and e['player']==q['player'] and e['hero']==q['hero'] and e['own_turn']==q['own_turn'] and e['op']==c['op']
  assert ai>si and a['native_request_id']==s['native_request_id'] and a['success'] is True
  nr=s['native_request_id'];server=log_records(log,'TypedActionApplied')
  matches=[r for r,li in server if r.get('player')==q['player'] and r.get('native_request_id')==nr];assert len(matches)==1 and matches[0]['success']==1
  if c['op']=='build':
   actual=s['actual_request'];assert actual['pack_type']=='BuildStructure' and actual['town_id']==c['town_id'] and actual['building_id']==c['building_id']
   bi,bstate=unique(events,lambda e:e['event']=='build_ack_state' and e['native_request_id']==nr)
   b,a=s['before_state'],bstate['state'];assert si<bi<ai and b['town_id']==a['town_id']==c['town_id'] and b['owner']==a['owner']==q['player']
   assert c['building_id'] not in b['buildings'] and c['building_id'] in a['buildings'] and set(b['buildings'])<=set(a['buildings']) and a['built_today']==b['built_today']+1
   for r in RES:assert a['resources'][r]==b['resources'][r]-c['cost'][r]
   matches=[r for r,li in log_records(log,'TypedBuildApplied') if r.get('native_request_id')==nr and r.get('player')==q['player']];assert len(matches)==1 and matches[0]['success']==1 and matches[0]['town_id']==c['town_id'] and matches[0]['building_id']==c['building_id']
  if c['op']=='recruit':
   assert q['economy_window_open'] and c['creature_id'] in ids
   actual=s['actual_request'];assert actual['pack_type']=='RecruitCreatures'
   for k in ['town_id','destination_army_id','creature_id','amount','level']:assert actual[k]==c[k]
   assert actual['player']==q['player'] and actual['native_request_id']==nr
   mi,state=unique(events,lambda e:e['event']=='recruit_ack_state' and e['native_request_id']==nr)
   assert si<mi<ai and state['before_state']==s['before_state'];recruit_state(c,state['before_state'],state['state'])
   assert state['before_state']['owner']==q['player']
   matches=[r for r,li in log_records(log,'TypedRecruitApplied') if r.get('native_request_id')==nr and r.get('player')==q['player']];assert len(matches)==1
   assert all(matches[0][k]==actual[k] for k in ['player','native_request_id','town_id','destination_army_id','creature_id','amount','level']) and matches[0]['success']==1
  checks.append(dict(decision_id=rid,op=c['op'],native_request_id=nr))
 # Coverage must use the actual first ownturn sequence, never selector phase alone.
 ops=[]
 if mechanism:
  prefix=[]
  for q,c,r in selected:
   prefix.append((q,c,r))
   if c['op']=='end_turn':break
  ops=[c['op'] for q,c,r in prefix];assert ops in [['build','recruit','move','recruit','end_turn'],['build','recruit','move','recruit','move','end_turn']],ops
  assert len({q['own_turn'] for q,c,r in prefix})==1 and all(q['economy_window_open'] for q,c,r in prefix)
  c1,c2=prefix[1][1],prefix[3][1];assert c1['amount']==c2['amount']==1 and c1['creature_id']==c2['creature_id'] and c1['town_id']==c2['town_id']
  move=prefix[2][1];assert move['kind']==3 and move['position']==move['next']
  assert sum(abs(a-b) for a,b in zip(move['next'],prefix[2][0]['from']))==1
  assert prefix[-1][0]['from']==prefix[0][0]['from']
 transfers=[]
 for si,s in enumerate(events):
  if s['event']!='free_transfer_native_sent':continue
  ai,a=unique(events,lambda e:e['event']=='free_transfer_ack_state' and e['native_request_id']==s['native_request_id'] and e['player']==s['player'])
  assert ai>si and a['success'] and a['before_state']==s['before_state'];transfer_state(s,a['before_state'],a['state'])
  matches=[r for r,li in log_records(log,'TypedFreeTransferApplied') if r.get('native_request_id')==s['native_request_id'] and r.get('player')==s['player']];assert len(matches)==1;server=matches[0]
  for k in ['player','native_request_id','source_army_id','target_army_id','from_slot','to_slot']:assert server[k]==s[k]
  assert server['what']==s['actual_what'] and server['val']==s['actual_val'] and server['success']==1
  transfers.append((si,ai,s))
 if mechanism:
  second_rid=prefix[3][0]['request_id'];end_rid=prefix[-1][0]['request_id']
  second_ack,_=unique(events,lambda e:e['event']=='package_applied' and e.get('decision_id')==second_rid)
  end_sent,_=unique(events,lambda e:e['event']=='native_action_sent' and e.get('decision_id')==end_rid)
  assert any(second_ack<si<ai<end_sent and s['creature_id']==c2['creature_id'] for si,ai,s in transfers),'no real same-species free transfer after second recruit before End'
 rawhashes={str(p.relative_to(work)):sha(p) for p in [work/'PLAN.json',work/'EXECUTION.json',work/'typed.jsonl',work/'client.log',catpath]+sorted((work/'agent').glob('request-*.json'))+sorted((work/'agent').glob('action-*.json'))}
 return dict(passed=True,whole_game_valid=True,native_game_completed=True,transport_drained=True,full_state_recruitment_verified=True,free_transfer_verified=True,mechanism_coverage_verified=mechanism,same_turn_build_recruit_move_recruit_return_end_verified=mechanism,catalog_runtime_bound=True,scope='raw native contract and state proof; no ability claim',raw=str(work),catalog_sha256=catsha,compiled_manifest_sha256=att['candidate_manifest_sha256'],actual_decisions_checked=len(checks),actual_recruits_checked=sum(c['op']=='recruit' for c in checks),actual_transfers_checked=len(transfers),one_turn_sequence=ops,checks=checks,drain=drain,source_sha256=plan['hashes'],raw_sha256=rawhashes,native_runs_by_auditor=0,gpu_runs=0,optimizer_steps=0)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--native',type=Path,required=True);p.add_argument('--whole-game',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
 try:result=audit_game(a.raw,a.native,mechanism=not a.whole_game)
 except Exception as e:
  (a.out/'AUDIT.json').write_text(json.dumps(dict(passed=False,error=repr(e),raw=str(a.raw)),indent=2)+'\n');raise
 (a.out/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
 (a.out/'events.jsonl').write_text((a.raw/'typed.jsonl').read_text())
 print(json.dumps({k:v for k,v in result.items() if k not in ['checks','drain','raw_sha256','source_sha256']},indent=2))
