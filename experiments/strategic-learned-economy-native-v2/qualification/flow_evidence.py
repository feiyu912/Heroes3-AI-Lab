"""Real stack-delta evidence. Full ArrangeStacks payload fields are NOT directly logged."""
import collections,hashlib,json,re
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def army(a):
 d=collections.Counter()
 for creature,count in a:
  assert type(creature) is int and creature>=0 and type(count) is int and count>0
  d[creature]+=count
 return d
def verify(raw,proposals,folder=None):
 assert folder is not None,'Own public trace and raw file binding required'
 folder=Path(folder);assert (folder/'client.log').read_text(errors='replace')==raw
 lines=[re.sub(r'\x1b\[[0-9;]*m','',s) for s in raw.splitlines()]
 owned=json.loads((folder/'PLAN.json').read_text())['owned_player']
 regs={};callbacks=[]
 for i,s in enumerate(lines,1):
  m=re.search(r'DirectorNativeRequestRegistered id=(\d+) player=(\d+) pack_type=(\d+) type=\d+(ArrangeStacks|RecruitCreatures|HireHero|BuildStructure)$',s)
  if m and int(m[2])==owned:
   identity=int(m[1]);assert identity not in regs
   regs[identity]=dict(id=identity,player=owned,pack_type=int(m[3]),type=m[4],registered_line=i)
  m=re.search(r'DirectorAI: economy request finished id=(\d+) success=([01])$',s)
  if m:
   identity=int(m[1]);assert identity in regs and m[2]=='1'
   callbacks.append(dict(**regs[identity],callback_line=i))
 trace=[json.loads(s) for s in (folder/'strategy-trace.jsonl').read_text().splitlines() if s]
 pairs=[];pending=None
 before_types={'before_army_transfer':'ArrangeStacks','before_recruit':'RecruitCreatures','before_hire_hero':'HireHero','before_build':'BuildStructure'}
 for row in trace:
  assert row['player']==owned
  if row['event'] in before_types:
   assert pending is None;pending=row
  if row['event'] in ('economy_applied','economy_failed'):
   assert pending is not None and row['event']=='economy_applied'
   pairs.append((pending,row));pending=None
 assert pending is None and len(pairs)==len(callbacks)
 transfers=[];first={}
 for p in proposals:first.setdefault(p['request']['own_turn'],p)
 for (before,after),actual in zip(pairs,callbacks):
  assert before_types[before['event']]==actual['type']
  if actual['type']!='ArrangeStacks':continue
  lo,hi=actual['registered_line'],actual['callback_line'];segment=lines[lo-1:hi]
  assert sum(bool(re.search(r'Received CPack of type \d+ArrangeStacks$',s)) for s in segment)==1
  assert sum(bool(re.search(r'Message \d+ArrangeStacks successfully applied!$',s)) for s in segment)==1
  changes=[s for s in segment if re.search(r'Received CPack of type \d+(RebalanceStacks|SwapStacks)$',s)]
  assert len(changes)==1,'Ambiguous/missing server stack mutation'
  generic=[i for i,s in enumerate(lines,1) if re.search(fr'DirectorNativeRequestAck id={actual["id"]} player={owned} pack_type={actual["pack_type"]} success=1$',s)]
  assert len(generic)==1 and generic[0]>hi
  for s in segment:
   if 'DirectorBuildPack ' in s:
    event=json.loads(s.split('DirectorBuildPack ',1)[1])
    assert not(event['event']=='set_resources_received' and event['player']==owned),'Free transfer changed own resources'
  assert all(before[k]==after[k] for k in ['gold','wood','ore','day','own_turn'])
  bh={h['id']:h for h in before['heroes']};ah={h['id']:h for h in after['heroes']};bt={t['id']:t for t in before['towns']};at={t['id']:t for t in after['towns']}
  assert bh.keys()==ah.keys() and bt.keys()==at.keys()
  hd=[h for h in bh if bh[h]!=ah[h]];td=[t for t in bt if bt[t]!=at[t]]
  assert len(hd)==len(td)==1
  hero,town=hd[0],td[0];hb,ha=bh[hero],ah[hero];tb,ta=bt[town],at[town]
  assert {k:v for k,v in hb.items() if k!='army'}=={k:v for k,v in ha.items() if k!='army'}
  assert {k:v for k,v in tb.items() if k!='army'}=={k:v for k,v in ta.items() if k!='army'}
  donated=army(tb['army'])-army(ta['army']);gained=army(ha['army'])-army(hb['army'])
  assert donated==gained and len(donated)==1
  assert army(tb['army'])+army(hb['army'])==army(ta['army'])+army(ha['army'])
  creature,count=next(iter(donated.items()));removed=[s for s in tb['army'] if s not in ta['army']]
  assert removed==[[creature,count]],'Not uniquely identifiable whole donor stack'
  turn=before['own_turn'];p=first.get(turn);assert p is not None
  q=p['request'];firstid=q['request_id']
  sent=[i for i,s in enumerate(lines,1) if 'DirectorTypedEvent ' in s and '"event":"native_action_sent"' in s and f'"decision_id":{firstid},' in s]
  assert len(sent)==1
  prewindow=hi<sent[0]
  if prewindow:
   assert q['hero']==hero and q['from']==[hb['x'],hb['y'],hb['z']] and q['economy_window_open'] is True
   assert (q['gold'],q['wood'],q['ore'])==(after['gold'],after['wood'],after['ore'])
  transfers.append(dict(**actual,generic_ack_line=generic[0],before=before,after=after,hero=hero,town=town,creature=creature,count=count,
   before_first_policy=prewindow,first_policy_request=firstid,first_policy_sent_line=sent[0],server_mutation=changes[0],
   payload_observation='native ID/player/type directly logged; donor/recipient and whole-stack amount uniquely reconstructed from public state plus compiled helper; slot IDs/what not directly logged',
   resource_evidence='gold/wood/ore exact unchanged; no own SetResources pack during actual transfer; first policy seven-resource state retained'))
 groups=[]
 for turn in sorted({t['before']['own_turn'] for t in transfers if t['before_first_policy']}):
  ts=[t for t in transfers if t['before']['own_turn']==turn and t['before_first_policy']]
  p=first[turn]['request'];last=ts[-1]
  assert p['hero']==last['hero']
  rescue=any(c['type']=='HireHero' and c['callback_line']<ts[0]['registered_line'] and b['own_turn']==turn for (b,a),c in zip(pairs,callbacks))
  groups.append(dict(own_turn=turn,prewindow_transfers=len(ts),rescue_hire_same_turn=rescue,first_policy_request=p,final_transfer_after=last['after']))
 return dict(passed=True,observed_transfers=len(transfers),prewindow_transfers=sum(t['before_first_policy'] for t in transfers),groups=groups,transfers=transfers,
  raw_sha256={n:sha(folder/n) for n in ['client.log','strategy-trace.jsonl','PLAN.json','agent/typed-broker.jsonl']},
  directly_observed_complete_arrange_payload=False,training_samples=0,optimizer_steps=0)
