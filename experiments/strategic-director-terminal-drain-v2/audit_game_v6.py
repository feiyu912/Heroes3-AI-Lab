"""New Director-owned terminal ACK scope; old v5/global-drain proof stays frozen."""
import collections,json,re,sys
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
TYPED=HERE.parent/'strategic-typed-native-v1'
sys.path.insert(0,str(TYPED))
sys.path.insert(0,str(HERE.parent/'strategic-policy-v3'))
from director_registry_v1 import verify as verify_registry,MARKER,whole_game_pass
from raw_events_v4 import extract
from broker import validate_response,digest
from audit_typed_execution import audit

folder=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
plan=json.loads((folder/'PLAN.json').read_text());owned=plan['owned_player']
assert plan['terminal_ack_scope']=='director'
raw=(folder/'client.log').read_text(errors='replace');events,mirror,lines,foreign=extract(raw,owned)
assert 'Script layer not found' not in raw
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
registry=verify_registry(raw,owned)
execution=json.loads((folder/'EXECUTION.json').read_text())
assert execution['terminal_ack_scope']=='director'
observed_game_over=any(e['event']=='game_over' and e.get('completed') is True for e in events)
native_completed=bool(observed_game_over and execution['client_exit']==0 and MARKER in raw)
transport_drained=bool(native_completed and registry['passed'])
observation_correction=bool(native_completed and not execution['game_completed'])
assert execution['input_sha_unchanged'] and execution['thread_server_verification']['passed']
assert all(o['valid'] for o in execution['loaded_library_observations'])
assert all(digest(Path(f).read_bytes())==h for f,h in plan['hashes'].items())
assert sum('/scripts/' in f for f in plan['hashes'])==41
assignment=dict(re.findall(r'Player ([a-z]+) will be lead by ([A-Za-z0-9]+)',raw))
assert assignment==dict(red='DirectorAI' if owned==0 else plan['opponent'],blue='DirectorAI' if owned==1 else plan['opponent'])
winner=None
if contract['valid'] and native_completed:
    assert 'All players have ended the game.' in raw
    endings=[r for r in map(json.loads,(folder/'strategy-trace.jsonl').read_text().splitlines()) if r['event'] in ('victory','defeat')]
    assert len(endings)==1 and endings[0]['player']==owned
    colour='red' if owned==0 else 'blue'
    # CDirectorAI logs every player callback before its playerID guard.
    native=[r for r in re.findall(r'DirectorAI: native gameOver player=(\w+) victory=([01]) loss=([01])',raw) if r[0]==colour]
    assert len(native)==1
    assert (native[0][1],native[0][2])==(('1','0') if endings[0]['event']=='victory' else ('0','1'))
    winner=colour if endings[0]['event']=='victory' else ('blue' if owned==0 else 'red')
rounds=0;actions=[];laststart=None;rejects=[]
for i,line in enumerate(raw.splitlines(),1):
    if 'Sending to all clients:' in line and re.search(r'\d+BattleStart(?:\x1b\[[0-9;]*m)?$',line):rounds=0;actions=[];laststart=i
    if 'Next round starts' in line:rounds+=1
    if 'Making action: ' in line:actions.append(line.split('Making action: ',1)[1])
    if any(t in line for t in ('Got false in applying','has to answer queries','DirectorTypedProtocolError')):rejects.append(i)
assert not rejects,rejects
counts=collections.Counter(actions[-1000:])
report=dict(whole_game_valid=whole_game_pass(contract['valid'],native_completed,transport_drained,execution['client_exit']),
    event_contract_valid=contract['valid'],native_game_completed=native_completed,transport_drained=transport_drained,
    terminal_ack_scope='director',director_registry_proof=registry,
    wrapper_terminal_observation_corrected=observation_correction,original_wrapper_game_completed=execution['game_completed'],
    winner=winner,owned_player=owned,actual_ai_assignment=assignment,
    raw_transport_consistent=True,training_samples=0,optimizer_steps=0,counts=contract['counts'],contract_errors=contract['errors'],
    native_apply_markers=sum(e['event']=='server_action_applied' for e in events),
    battle_observation=dict(last_battle_start_line=laststart,round_start_count=rounds,native_battle_actions=len(actions),unique_last1000_actions=len(counts),top_last1000_actions=counts.most_common(8)),
    raw_sha256={n:digest((folder/n).read_bytes()) for n in ('client.log','typed.jsonl','strategy-decisions.jsonl','EXECUTION.json','PLAN.json')},
    auditor_sha256={p.name:digest(p.read_bytes()) for p in [Path(__file__),TYPED/'raw_events_v4.py',HERE/'director_registry_v1.py']},
    limitation='Director requests require actual ACKs; explicitly terminated foreign waits are not ACKed or successful. Whole-game completion also requires exit0. Timeout has no reward or optimizer update.')
(out/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events));(out/'WHOLE_GAME_CONTRACT.json').write_text(json.dumps(contract,indent=2));(out/'AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['whole_game_valid'] else 1)
