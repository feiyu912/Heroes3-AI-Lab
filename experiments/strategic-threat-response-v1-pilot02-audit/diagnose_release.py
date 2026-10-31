"""Read-only binding effect counts and pre-trigger causal limits."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
RUN=HERE.parent/'strategic-threat-response-v1/native-pilot-02'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return [json.loads(s)for s in p.read_text().splitlines()]
out=[]
for i in range(8):
 a=load(RUN/'candidate'/f'{i:02d}'/'RAW_AUDIT.json');agent=Path(a['raw']['agent_dir'])
 ds=rows(Path(a['raw']['native_dir'])/'strategy-decisions.jsonl');proofs=[]
 for p in a['release_proofs']:
  request=load(agent/f'request-{p["request_id"]:08d}.json');prior=p['prior_commit']
  old_indices=[j for j,c in enumerate(request['candidates'])if c['position']==prior['destination']and c['kind']==prior['kind']]
  d=ds[p['request_id']-1];chosen=request['candidates'][d['selected_candidate']]
  binding=bool(old_indices)
  proofs.append(dict(trace_line=p['trace_line'],request_id=p['request_id'],day=request['day'],
   prior_commit_present=binding,full_candidate_count=len(request['candidates']),
   additional_candidate_slots=len(request['candidates'])-1 if binding else 0,
   selected_new_goal=bool(binding and(chosen['position']!=prior['destination']or chosen['kind']!=prior['kind'])),
   prior_commit=prior,chosen=chosen,request_sha256=sha(agent/f'request-{p["request_id"]:08d}.json')))
 out.append(dict(pair_index=i,releases=len(proofs),binding=sum(p['prior_commit_present']for p in proofs),
  nonbinding=sum(not p['prior_commit_present']for p in proofs),added_candidate_slots=sum(p['additional_candidate_slots']for p in proofs),
  binding_selected_new_goal=sum(p['selected_new_goal']for p in proofs),first_release=proofs[:1],proofs=proofs))

causal={}
for arm in ('baseline','candidate'):
 a=load(RUN/arm/'07/RAW_AUDIT.json');raw=a['raw'];root=Path(raw['native_dir']);agent=Path(raw['agent_dir'])
 text=(root/'client.log').read_text().splitlines();clean=[re.sub(r'\x1b\[[0-9;]*m','',s)for s in text]
 cut=[i for i,s in enumerate(text)if'DirectorAI: step hero'in s][16]
 npc=[dict(line=i+1,text=s)for i,s in enumerate(clean[:cut])if'wants to move hero'in s and'Player 0'in s]
 request=load(agent/'request-00000017.json');d=rows(root/'strategy-decisions.jsonl')[16]
 moves=rows(root/'strategy-decisions.jsonl');states=rows(root/'strategy-trace.jsonl');absent=raw['original_main_first_absent']
 before=states[:absent['line']-1]if absent else states
 block=next((j for j in range(len(before)-1,-1,-1)if before[j]['event']=='native_battle_blocked'),None)
 driver=next((s['event']for s in reversed(before[:block])if s['event']in ('before_move','turn_end','turn_start')),None)if block is not None else None
 removal=[dict(line=i+1,text=s)for i,s in enumerate(clean)if f'removing object id={raw["original_main_id"]};'in s]
 causal[arm]=dict(request17={k:v for k,v in request.items()if k!='candidates'},selected17=request['candidates'][d['selected_candidate']],
  request17_sha256=sha(agent/'request-00000017.json'),npc_move_prefix=npc,
  first_absent=absent,main_status=raw['original_main_status'],loss_battle_driver=driver,main_removal_log=removal,
  native_dir=str(root),log_sha256=sha(root/'client.log'))
nb,nc=causal['baseline']['npc_move_prefix'],causal['candidate']['npc_move_prefix']
first_npc=next((i for i,(b,c)in enumerate(zip(nb,nc))if b['text']!=c['text']),None)
if first_npc is None and len(nb)!=len(nc):first_npc=min(len(nb),len(nc))
evidence=dict(schema='threat-response-binding-and-trigger-audit-v1',episodes=out,
 totals={key:sum(r[key]for r in out)for key in ('releases','binding','nonbinding','added_candidate_slots','binding_selected_new_goal')},
 pair7=causal,first_npc_move_difference_index=first_npc,
 interpretation='Paired observed score -1 is not clean release-caused harm: pair7 action/world divergence precedes every release and original hero death precedes first release. No timing/RNG cause established.')
target=HERE/'BINDING_AND_CAUSAL_LIMIT.json';assert not target.exists();target.write_text(json.dumps(evidence,indent=2))
print(json.dumps(evidence['totals']))
print('first NPC difference',first_npc)
if first_npc is not None:
 print('baseline',nb[first_npc]if first_npc<len(nb)else None)
 print('candidate',nc[first_npc]if first_npc<len(nc)else None)
