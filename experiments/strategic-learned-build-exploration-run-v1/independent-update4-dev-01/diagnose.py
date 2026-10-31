"""Read public own-state and bound policy requests; never load game-state/save/map objects."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
LAB=Path('/root/heroes3-ai-lab');DEV=LAB/'evaluations/strategic-build-exploration-update4-dev-01'
CAP=LAB/'evaluations/strategic-learned-economy-build-capsule-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def load(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def clean(s):return re.sub(r'\x1b\[[0-9;]*m','',s)
def one(lines,pred):
 a=[(i+1,s) for i,s in enumerate(lines) if pred(s)];assert len(a)==1,a
 return dict(line=a[0][0],text=a[0][1])
cases=[]
for pair in [2,3,6,7]:
 n=DEV/f'pair-{pair:02d}/b/native';audit=load(n.parent/'raw-audit/AUDIT.json')
 assert all(sha(n/p)==h for p,h in audit['raw_sha256'].items())
 ps=rows(n/'agent/typed-broker.jsonl');last=ps[-1];q=last['request'];typed=rows(n/'typed.jsonl');trace=rows(n/'strategy-trace.jsonl');lines=[clean(s) for s in (n/'client.log').read_text().splitlines()]
 death=next(x for x in reversed(trace) if x['event']=='defeat')
 own=[]
 for p in ps:
  for town in p['request']['own_towns']:
   own.append(dict(request=p['request']['request_id'],day=p['request']['day'],town=town))
 latest={}
 for x in own:latest[x['town']['town_id']]=x
 entry=dict(pair=pair,last_request=q,last_response=last['response'],terminal_public_own_trace=death,last_seen_own_towns=list(latest.values()),
  client_sha256=sha(n/'client.log'),typed_sha256=sha(n/'typed.jsonl'),auxiliary_trace_sha256=sha(n/'strategy-trace.jsonl'),
  auxiliary_trace_in_original_raw_certificate='strategy-trace.jsonl' in audit['raw_sha256'],
  native_tail=[dict(line=i+1,text=s) for i,s in enumerate(lines) if any(k in s for k in ['DaysWithoutTown','PlayerEndsGame','BattleResultsApplied','RemoveObject','native_game_over'])][-16:])
 if pair in [3,7]:
  firstq=160 if pair==3 else 274
  p=next(x for x in ps if x['request']['request_id']==firstq);q0=p['request'];q1=next(x['request'] for x in ps if x['request']['request_id']==firstq+1)
  ev=next(e for e in typed if e['event']=='native_action_sent' and e.get('decision_id')==firstq);mid=ev['native_request_id'];hid=mid-1
  hire=one(lines,lambda s:f'DirectorNativeRequestRegistered id={hid} ' in s and 'HireHero' in s)
  callback=one(lines,lambda s:f'DirectorAI: economy request finished id={hid} success=1' in s)
  ack=one(lines,lambda s:f'DirectorNativeRequestAck id={hid} ' in s and 'success=1' in s)
  move=one(lines,lambda s:'DirectorTypedEvent ' in s and f'"decision_id":{firstq},' in s and '"event":"native_action_sent"' in s)
  moveack=one(lines,lambda s:'DirectorTypedEvent ' in s and f'"decision_id":{firstq},' in s and '"event":"package_applied"' in s)
  nxt=one(lines,lambda s:'DirectorTypedEvent ' in s and f'"decision_id":{firstq+1},' in s and '"event":"native_action_sent"' in s)
  assert hire['line']<callback['line']<move['line']<moveack['line']<nxt['line']
  noarr=[dict(line=i+1,text=s) for i,s in enumerate(lines) if hire['line']<=i+1<=nxt['line'] and 'ArrangeStacks' in s];assert not noarr
  ts=[x for x in trace if x['own_turn']==q0['own_turn']]
  firstmove=next(i for i,x in enumerate(ts) if x['event']=='move_applied')
  prefix=ts[:firstmove+1]
  before=next(x for x in prefix if x['event']=='before_move');after=prefix[-1]
  hero0=before['heroes'][0];hero1=after['heroes'][0];town0=before['towns'][0];town1=after['towns'][0]
  assert hero0['army']==hero1['army'] and town0['army']==town1['army']
  assert [hero0[k] for k in ['x','y','z']]==q0['from']==q0['own_towns'][0]['position']
  assert len(hero0['army'])==1 and len(town0['army'])<=6 and not ({x[0] for x in hero0['army']}&{x[0] for x in town0['army']})
  assert q0['own_army_value']==q1['own_army_value'] and q0['own_towns'][0]['army_value']==q1['own_towns'][0]['army_value']
  entry['stranded_stock']=dict(first_request=q0,next_request=q1,chosen=ev,trace_through_first_move=prefix,hire_registered=hire,hire_actual_callback=callback,hire_generic_ack=ack,move_sent=move,move_actual_ack=moveack,next_move_sent=nxt,arrange_in_interval=noarr,free_recipient_slots=7-len(hero0['army']),distinct_donor_stacks=len(town0['army']),same_town_start=True)
 cases.append(entry)
compiled=load(CAP/'build-source-manifest.json');proof={}
for rel in ['AI/DirectorAI/CDirectorAI.cpp','AI/DirectorAI/CDirectorAI.h','lib/mapObjects/army/CCreatureSet.cpp','lib/mapObjects/army/CCreatureSet.h','lib/callback/CCallback.cpp','server/processors/NewTurnProcessor.cpp','lib/gameState/CGameState.cpp']:
 p=CAP/'source-snapshot'/rel
 if not p.exists():p=LAB/'src/vcmi-adv'/rel
 assert sha(p)==compiled[rel]['sha256'],rel
 proof[rel]=dict(actual_path=str(p),sha256=sha(p),matches_compiled_source_manifest=True)
train=[]
roots=[LAB/'evaluations/strategic-learned-build-exploration-train-01']+[LAB/f'evaluations/strategic-build-exploration-continuation-01/round-{i:02d}' for i in [2,3,4]]
for update,root in enumerate(roots,1):
 for cell in [2,3,6,7]:
  case=root/f'cell-{cell:02d}';n=case/'native';a=load(case/'raw-audit/AUDIT.json')
  assert all(sha(n/p)==h for p,h in a['raw_sha256'].items())
  ps=rows(n/'agent/typed-broker.jsonl');q=ps[-1]['request'];tr=rows(n/'strategy-trace.jsonl')
  train.append(dict(update=update,cell=cell,case=str(case),winner=a['winner'],owned_player=load(n/'PLAN.json')['owned_player'],last_request=q,terminal_public_own_trace=next(x for x in reversed(tr) if x['event']=='defeat'),client_sha256=sha(n/'client.log'),auxiliary_trace_sha256=sha(n/'strategy-trace.jsonl'),validation='existing raw certificate hashes checked, auditor not rerun for TRAIN here'))
write(HERE/'FAILURE_EVIDENCE.json',dict(final_dev=cases,compiled_source_proof=proof,train_nk=train,no_hidden_state_read=True,new_native_runs=0,new_gpu_runs=0))
print('Saved evidence: four final DEV NK, two rescue/free-stock intervals, sixteen TRAIN NK, compiled source proof')
