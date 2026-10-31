"""Independent CPU-only paired04 raw/proof and recorded-prefix review."""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPLAN=HERE.parent/'strategic-threat-replan-v2'
sys.path.insert(0,str(REPLAN))
from causal_stability_audit_v2 import rows,sha,first_difference,policy_action,parse_log,movement_comparison,stability
LAB=Path('/root/heroes3-ai-lab')

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    base=LAB/'evaluations/typed-clearance-proxy-paired-04'
    result=json.loads((base/'RESULT.json').read_text());assert result['passed'] and len(result['pairs'])==8
    plan=json.loads((base/'PLAN.json').read_text());assert all(sha(Path(p))==h for p,h in plan['input_sha256'].items())
    a.out.mkdir(parents=True,exist_ok=False);pairs=[];inputs={str(p):sha(p) for p in [Path(__file__),base/'RESULT.json',base/'PLAN.json']}
    for old in result['pairs']:
        number=old['pair'];arms={}
        for arm in ['a','b']:
            folder=base/f'pair-{number:02d}'/arm;root=folder/'native';out=a.out/f'pair-{number:02d}'/arm;out.mkdir(parents=True)
            before={str(p):sha(p) for p in root.rglob('*') if p.is_file()}
            # Check existing three audit proofs against their current source/raw bindings too.
            for kind in ['raw-audit','replan-audit','proxy-audit']:
                proof_path=folder/kind/'AUDIT.json';proof=json.loads(proof_path.read_text());inputs[str(proof_path)]=sha(proof_path)
                assert proof.get('passed',proof.get('whole_game_valid')) is True
                for field in ['input_sha256']:
                    assert all(sha(Path(p))==h for p,h in proof.get(field,{}).items())
                if kind=='raw-audit':
                    assert all(sha(root/p)==h for p,h in proof['raw_sha256'].items())
                    expected={'audit_game_v6.py':HERE/'audit_game_v6.py','director_registry_v1.py':HERE/'director_registry_v1.py','raw_events_v4.py':HERE.parent/'strategic-typed-native-v1/raw_events_v4.py'}
                    assert all(sha(expected[p])==h for p,h in proof['auditor_sha256'].items())
            commands=[['/usr/bin/python3',HERE/'audit_game_v6.py',root,out/'raw-audit'],
                      ['/usr/bin/python3',HERE/'audit_replan_v3.py',root,out/'raw-audit/AUDIT.json',out/'replan-audit'],
                      [LAB/'venv/bin/python',REPLAN/'audit_proxy.py',root,out/'replan-audit/AUDIT.json',out/'proxy-audit']]
            for i,command in enumerate(commands):
                r=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=120)
                (out/f'command-{i}.log').write_text(r.stdout+'\nSTDERR:\n'+r.stderr);assert r.returncode==0,(number,arm,i,r.stderr)
            proof=json.loads((out/'raw-audit/AUDIT.json').read_text());proxy=json.loads((out/'proxy-audit/AUDIT.json').read_text());replan=json.loads((out/'replan-audit/AUDIT.json').read_text())
            assert proof['whole_game_valid'] and proof['audit_epoch']=='director-neutral-makeaction-ack-v4' and not proof['read_only_legacy_reaudit']
            assert all(sha(Path(p))==h for p,h in before.items());inputs.update(before)
            proposals=rows(root/'agent/typed-broker.jsonl');parsed=parse_log((root/'client.log').read_text(errors='replace'))
            terminal=next(x for x in rows(root/'strategy-trace.jsonl') if x['event'] in ['victory','defeat'])
            arms[arm]=dict(root=root,proposals=proposals,parsed=parsed,proxy=proxy,summary=dict(winner=proof['winner'],win=proof['winner']==('red' if old['job']['player']==0 else 'blue'),
                          day=terminal['day'],counts=proof['counts'],releases=replan['releases'],overrides=proxy['overrides'],registered=proof['director_registry_proof']['registered_count'],
                          actual_atomic_cleared_ids=proof['director_registry_proof']['actual_atomic_cleared_ids'],neutral_ack_count=proof['director_registry_proof']['verified_neutral_makeaction_ack_count'],
                          stability=stability(proposals,rows(root/'typed.jsonl'),parsed,128)))
        left,right=arms['a'],arms['b'];qs=[[p['request'] for p in arm['proposals']] for arm in [left,right]]
        actions=[[policy_action(p) for p in arm['proposals']] for arm in [left,right]]
        first=min((e['decision_id'] for e in right['proxy']['details']),default=None);prefix=None
        if first is not None:
            # Both arms emit a real bounded release before publishing this identical request.
            anchors=[];moves=[]
            for arm in [left,right]:
                matching=[e for e in arm['parsed']['releases'] if e['event']['decision_id']==first];assert len(matching)==1
                anchor=matching[0];anchors.append(anchor)
                moves.append([e for e in arm['parsed']['movements'] if e['line']<anchor['line']])
            prefix=movement_comparison(*moves)
            prefix.update(decision_id=first,anchors=anchors,anchor_definition='Strictly before actual matching bounded-release log line in each arm; includes all server movements, including NPCs.',
                          requests_through_override_identical=qs[0][:first]==qs[1][:first],
                          action_file_bytes_identical_before_override=all((left['root']/f'agent/action-{n:08d}.json').read_bytes()==(right['root']/f'agent/action-{n:08d}.json').read_bytes() for n in range(1,first)),
                          request_file_bytes_identical_through_override=all((left['root']/f'agent/request-{n:08d}.json').read_bytes()==(right['root']/f'agent/request-{n:08d}.json').read_bytes() for n in range(1,first+1)),
                          first_override_detail=next(e for e in right['proxy']['details'] if e['decision_id']==first))
        pair=dict(pair=number,job=old['job'],arms={k:v['summary'] for k,v in arms.items()},request_counts=list(map(len,qs)),
                  first_request_difference=first_difference(*qs),first_observation_difference=first_difference(*[[{k:v for k,v in q.items() if k!='candidates'} for q in sequence] for sequence in qs]),
                  first_policy_action_difference=first_difference(*actions),first_override=first,pre_first_override=prefix,
                  all_server_movement_comparison=movement_comparison(left['parsed']['movements'],right['parsed']['movements']))
        pair['win_delta']=int(pair['arms']['b']['win'])-int(pair['arms']['a']['win']);assert pair['win_delta']==old['win_delta']
        pairs.append(pair);(a.out/'PROGRESS.json').write_text(json.dumps(dict(pairs_completed=len(pairs)),indent=2));print('reviewed pair',number,flush=True)
    totals=dict(model_wins=sum(p['arms']['a']['win'] for p in pairs),proxy_wins=sum(p['arms']['b']['win'] for p in pairs),net_wins=sum(p['win_delta'] for p in pairs),overrides=sum(p['arms']['b']['overrides'] for p in pairs))
    assert all(totals[k]==result[k] for k in totals);assert all(sha(Path(p))==h for p,h in inputs.items())
    report=dict(passed=True,fixture=False,whole_game_execution_reaudited=True,native_games_reaudited=16,new_native_games=0,GPU_operations=0,optimizer_steps=0,training_samples=0,expert_labels=0,finaltest_touched=False,
                totals=totals,pairs=pairs,input_sha256=inputs,original_result_sha256=sha(base/'RESULT.json'),ability_improvement_claim=False,
                limitation='Same selected development cells and scripted coordinate proxy. Prefix equality covers recorded requests, observations and server movement projection, not complete hidden state or general causal superiority; no neural training or human tactical gain.')
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(dict(passed=True,totals=totals),indent=2))

if __name__=='__main__':main()
