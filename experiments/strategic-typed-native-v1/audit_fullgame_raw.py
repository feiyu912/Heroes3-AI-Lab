"""Raw transport + whole-game gate, retaining timeout as unscored invalid game."""
import collections,json,re,sys
from pathlib import Path
from audit_smoke_raw import extract
from broker import validate_response,digest
from audit_typed_execution import audit

folder=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
raw=(folder/'client.log').read_text(errors='replace');events,mirror,lines,foreign=extract(raw)
assert mirror==[json.loads(s) for s in (folder/'typed.jsonl').read_text().splitlines()]
proposals=[json.loads(s) for s in (folder/'agent/typed-broker.jsonl').read_text().splitlines()]
for p in proposals:
    identity=p['request']['request_id'];data=(folder/f'agent/request-{identity:08d}.json').read_bytes()
    assert json.loads(data)==p['request'];validate_response(p['response'],p['request'],data)
    assert json.loads((folder/f'agent/action-{identity:08d}.json').read_bytes())==p['response']
decisions=[json.loads(s) for s in (folder/'strategy-decisions.jsonl').read_text().splitlines()]
moves=[p for p in proposals if p['response']['op']=='move'];assert len(decisions)==len(moves)
for d,p in zip(decisions,moves):
    q=p['request'];r=p['response'];c=q['candidates'][r['selected_index']]
    assert (d['player'],d['hero'],d['day'],d['from'])==(q['player'],q['hero'],q['day'],q['from'])
    assert d['selected_candidate']==r['selected_index'] and d['candidates']==q['candidates']
    assert d['destination']==c['position'] and d['step']==c['next']
contract=audit(proposals,events,fixture=False)
execution=json.loads((folder/'EXECUTION.json').read_text())
assert execution['input_sha_unchanged'] and execution['thread_server_verification']['passed']
assert all(o['valid'] for o in execution['loaded_library_observations'])
plan=json.loads((folder/'PLAN.json').read_text());assert all(digest(Path(f).read_bytes())==h for f,h in plan['hashes'].items())
rounds=0;actions=[];laststart=None;rejects=[]
for i,line in enumerate(raw.splitlines(),1):
    if 'Sending to all clients:' in line and re.search(r'\d+BattleStart(?:\x1b\[[0-9;]*m)?$',line):rounds=0;actions=[];laststart=i
    if 'Next round starts' in line:rounds+=1
    if 'Making action: ' in line:actions.append(line.split('Making action: ',1)[1])
    if any(t in line for t in ('Got false in applying','has to answer queries','DirectorTypedProtocolError')):rejects.append(i)
assert not rejects,rejects
counts=collections.Counter(actions[-1000:])
report=dict(whole_game_valid=contract['valid'],native_game_completed=execution['game_completed'],winner=None,
    raw_transport_consistent=True,training_samples=0,optimizer_steps=0,counts=contract['counts'],contract_errors=contract['errors'],
    native_apply_markers=sum(e['event']=='server_action_applied' for e in events),
    battle_observation=dict(last_battle_start_line=laststart,round_start_count=rounds,native_battle_actions=len(actions),unique_last1000_actions=len(counts),top_last1000_actions=counts.most_common(8)),
    raw_sha256={n:digest((folder/n).read_bytes()) for n in ('client.log','typed.jsonl','strategy-decisions.jsonl','EXECUTION.json','PLAN.json')},
    limitation='Consistency of executed requests is separate from a completed strategic game. Timeout has no reward or optimizer update.')
(out/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events));(out/'WHOLE_GAME_CONTRACT.json').write_text(json.dumps(contract,indent=2));(out/'AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
