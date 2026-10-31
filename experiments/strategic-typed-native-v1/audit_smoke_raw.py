"""Cross-certify a nonterminal typed transport prefix; never invent game_over."""
import copy,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'strategic-policy-v3'))
from broker import validate_response,digest
from audit_typed_execution import audit,BINDING

def extract(raw):
    events=[];client_events=[];bindings={};lines=[];foreign=[]
    for number,line in enumerate(raw.splitlines(),1):
        line=re.sub(r'\x1b\[[0-9;]*m','',line)
        if 'DirectorTypedEvent ' in line:
            event=json.loads(line.split('DirectorTypedEvent ',1)[1]);client_events.append(event)
            if event['event']=='native_action_sent':
                key=(event['player'],event['native_request_id'],event['op'])
                assert key not in bindings;bindings[key]=event
            assert event['event']!='typed_protocol_error'
            events.append(event);lines.append(number)
        elif 'TypedActionApplied ' in line:
            m=re.search(r'TypedActionApplied player=(\d+) native_request_id=(\d+) op=(move|end_turn) success=([01])$',line)
            assert m,'Malformed actual apply marker'
            player,identity,op,success=int(m[1]),int(m[2]),m[3],int(m[4]);key=(player,identity,op)
            if player!=0:foreign.append(dict(line=number,player=player,request_id=identity));continue
            assert success==1 and key in bindings,'Server rejected or unbound native apply'
            event={k:bindings[key][k] for k in BINDING};event.update(event='server_action_applied',source='server',success=True)
            events.append(event);lines.append(number)
    return events,client_events,lines,foreign

def main():
    folder=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
    raw=(folder/'client.log').read_text(errors='replace')
    assert not any(t in raw for t in ('Got false in applying','has to answer queries','DirectorTypedProtocolError'))
    events,mirror,lines,foreign=extract(raw)
    assert mirror==[json.loads(s) for s in (folder/'typed.jsonl').read_text().splitlines()]
    proposals=[json.loads(s) for s in (folder/'agent/typed-broker.jsonl').read_text().splitlines()]
    assert len(proposals)==4
    for p in proposals:
        identity=p['request']['request_id'];data=(folder/f'agent/request-{identity:08d}.json').read_bytes()
        assert json.loads(data)==p['request']
        validate_response(p['response'],p['request'],data)
        assert json.loads((folder/f'agent/action-{identity:08d}.json').read_bytes())==p['response']
    contract=audit(proposals,events,fixture=False)
    assert not contract['valid'] and contract['errors']==[{'error':'No native game_over completion'}],contract['errors']
    assert contract['counts']['policy_moves']==2 and contract['counts']['policy_end_turns']==2
    assert contract['counts']['diagnostic_decisions']==4 and contract['counts']['new_policy_decisions']==0
    decisions=[json.loads(s) for s in (folder/'strategy-decisions.jsonl').read_text().splitlines()]
    moves=[p for p in proposals if p['response']['op']=='move'];assert len(decisions)==len(moves)
    for d,p in zip(decisions,moves):
        q=p['request'];r=p['response'];c=q['candidates'][r['selected_index']]
        assert d['player']==q['player'] and d['hero']==q['hero'] and d['day']==q['day'] and d['from']==q['from']
        assert d['selected_candidate']==r['selected_index'] and d['candidates']==q['candidates']
        assert d['destination']==c['position'] and d['step']==c['next']
    # The original whole-game gate MUST reject this real nonterminal prefix.
    # Missing/false actual service result and wrong saved ACK turn must also fail.
    rejected=[]
    bad=copy.deepcopy(events);next(e for e in bad if e['event']=='server_action_applied' and e['op']=='end_turn')['success']=False
    assert len(audit(proposals,bad)['errors'])>1;rejected.append('false_actual_end_turn_result')
    bad=[e for e in events if not(e['event']=='server_action_applied' and e.get('decision_id')==2)]
    assert len(audit(proposals,bad)['errors'])>1;rejected.append('missing_actual_end_turn_apply')
    bad=copy.deepcopy(events);next(e for e in bad if e['event']=='package_applied' and e['op']=='end_turn')['own_turn']+=1
    assert len(audit(proposals,bad)['errors'])>1;rejected.append('wrong_saved_ack_turn')
    execution=json.loads((folder/'EXECUTION.json').read_text());assert execution['controlled_stop'] and execution['input_sha_unchanged'] and execution['thread_server_verification']['passed']
    assert all(o['valid'] for o in execution['loaded_library_observations'])
    result=dict(prefix_mechanism_pass=True,full_game_valid=False,game_completed=False,winner=None,optimizer_steps=0,training_samples=0,
        policy_moves=2,policy_end_turns=2,diagnostic_decisions=4,counts=contract['counts'],
        whole_game_rejection_preserved=contract['errors'],negative_cases=rejected,foreign_server_markers=foreign,
        raw_line_for_event=lines,input_sha256={str(p):digest(p.read_bytes()) for p in [folder/'client.log',folder/'typed.jsonl',folder/'strategy-decisions.jsonl',folder/'agent/typed-broker.jsonl',Path(__file__)]})
    (out/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events));(out/'WHOLE_GAME_CONTRACT.json').write_text(json.dumps(contract,indent=2));(out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
