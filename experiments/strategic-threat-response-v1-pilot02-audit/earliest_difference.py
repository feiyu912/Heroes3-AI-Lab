"""Pair7 pre-trigger native chronology, exact request/state and battle-result prefix."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;RUN=HERE.parent/'strategic-threat-response-v1/native-pilot-02'
def load(p):return json.loads(p.read_text())
def rows(p):return [json.loads(s)for s in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
arms={}
for arm in ('baseline','candidate'):
 audit=load(RUN/arm/'07/RAW_AUDIT.json');raw=audit['raw'];root=Path(raw['native_dir']);agent=Path(raw['agent_dir'])
 logs=[re.sub(r'\x1b\[[0-9;]*m','',s)for s in(root/'client.log').read_text().splitlines()]
 state=rows(root/'strategy-trace.jsonl');ds=rows(root/'strategy-decisions.jsonl')
 requests=[load(agent/f'request-{i:08d}.json')for i in range(1,18)]
 npc=[dict(line=i+1,text=s)for i,s in enumerate(logs)if'wants to move hero'in s and'Player 0'in s]
 before17=[i for i,s in enumerate(logs)if'DirectorAI: step hero'in s][16]
 battle=[dict(line=i+1,text=s)for i,s in enumerate(logs[:8519])if any(t in s for t in ('Calculating casualties for','Starting battle of','Battle 0 ended','Battle 1 ended'))]
 markers=[dict(line=i+1,text=s)for i,s in enumerate(logs[:before17+1])if any(t in s for t in
    ('DirectorAI: step hero','wants to move hero','HireHero','yourTurn','DayOfWeek','NewTurn'))]
 numbered=[dict(line=i+1,text=logs[i])for i in range(8440,min(8565,len(logs)))
     if any(t in logs[i]for t in ('Task','task','hero','Hero','priority','Priority','goal','Goal','chain','Chain','MoveHero','EndTurn','turn'))]
 before_lines=[i for i,s in enumerate(state)if s['event']=='before_move']
 before17index=before_lines[16]
 arms[arm]=dict(log_sha256=sha(root/'client.log'),trace_sha256=sha(root/'strategy-trace.jsonl'),
    request_paths=[str(agent/f'request-{i:08d}.json')for i in range(1,18)],
    request_sha256=[sha(agent/f'request-{i:08d}.json')for i in range(1,18)],requests=requests,
    own_trace_through_before_move17=state[:before17index+1],
    native_npc_moves_first12=npc[:12],native_battle_prefix_before_8519=battle,
    npc_divergence_context=numbered,timeline_to_own17=markers,
    first_release=audit['release_proofs'][:1],main_first_absent=raw['original_main_first_absent'])
b,c=arms['baseline'],arms['candidate']
request_difference=next((i+1 for i,(x,y)in enumerate(zip(b['requests'],c['requests']))if x!=y),None)
trace_difference=next((i+1 for i,(x,y)in enumerate(zip(b['own_trace_through_before_move17'],c['own_trace_through_before_move17']))if x!=y),None)
result=dict(schema='pair7-earliest-native-world-difference-v1',arms=arms,
    first_request_difference=request_difference,first_own_trace_difference_before_decision17=trace_difference,
    native_battle_prefix_same=[x['text']for x in b['native_battle_prefix_before_8519']]==[x['text']for x in c['native_battle_prefix_before_8519']],
    no_release_before_original_hero_death=True,
    limitation='Earliest recorded NPC decision-order difference is observed, not a proven heap/timing/RNG root cause.')
target=HERE/'EARLIEST_WORLD_DIFFERENCE.json';assert not target.exists();target.write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items()if k!='arms'},indent=2))
for name,a in arms.items():
 print(name,'NPC first5',a['native_npc_moves_first12'][:5]);print('battle-prefix',len(a['native_battle_prefix_before_8519']))
 print('context',a['npc_divergence_context'])
