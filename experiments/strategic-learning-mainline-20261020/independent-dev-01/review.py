"""All completed DEV arms and recorded-prefix causal/stability diagnosis; CPU only."""
import collections,hashlib,json,re,subprocess,sys
from pathlib import Path
import torch
SOURCE=Path(__file__).resolve();HERE=SOURCE.parent.parent;OUT=HERE/'independent-dev-final-01';E=HERE.parent
sys.path.insert(0,str(E/'strategic-typed-training-v1'));sys.path.insert(0,str(E/'strategic-threat-replan-v2'))
from model_io import load_model
from episode_balanced_ppo import collate
from causal_stability_audit_v2 import parse_log,policy_action,first_difference,movement_comparison,stability
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
B=Path('/root/heroes3-ai-lab/evaluations/strategic-mainline-temperature2-dev-01')
def rows(p):return [json.loads(s) for s in p.read_text().splitlines()]
def short_diff(a,b):
    d=first_difference(a,b)
    if d:return dict(index=d['index'],a_eof=d['off_eof'],b_eof=d['once_eof'])
def actual_edges(parsed,name):return [tuple(x['start']+x['end']) for x in parsed['movements'] if x['hero_log_name']==name]
def main():
    OUT.mkdir(exist_ok=False);torch.set_num_threads(1);result=json.loads((B/'RESULT.json').read_text());plan=json.loads((B/'PLAN.json').read_text())
    assert result['passed'] and len(result['pairs'])==8 and result['optimizer_steps']==result['training_samples']==0
    assert all(sha(p)==h for p,h in plan['input_sha256'].items());assert plan['sampling']=='CPU argmax' and plan['threat_replan']=='off'
    assert [j['seed'] for j in plan['jobs']]==list(range(2026102100,2026102108))
    models={a:load_model(p,'cpu')[0] for a,p in plan['model_paths'].items()};pairs=[];paths=[SOURCE,B/'PLAN.json',B/'RESULT.json'];all_stop=0
    for i,pair in enumerate(result['pairs']):
        arms={};data={}
        for arm in ('a','b'):
            root=B/f'pair-{i:02d}'/arm;native=root/'native';target=OUT/f'pair-{i:02d}'/arm
            target.mkdir(parents=True,exist_ok=False)
            subprocess.run([sys.executable,str(E/'strategic-director-terminal-drain-v4/audit_game_v6.py'),str(native),str(target/'raw-audit')],check=True,capture_output=True,text=True)
            proof=json.loads((target/'raw-audit/AUDIT.json').read_text());assert proof==json.loads((root/'raw-audit/AUDIT.json').read_text())
            proposals=rows(native/'agent/typed-broker.jsonl');typed=rows(native/'typed.jsonl');trace=rows(native/'strategy-trace.jsonl');parsed=parse_log((native/'client.log').read_text());terminal=[e for e in trace if e['event'] in ('victory','defeat')];assert len(terminal)==1
            np=json.loads((native/'PLAN.json').read_text());assert np['decision_policy']=='model' and np['threat_replan']=='off' and sha(np['checkpoint'])==sha(plan['model_paths'][arm])
            counts=collections.Counter();margins={};all_replays=[]
            for p in proposals:
                q=p['request'];r=p['response'];assert r['classification']=='new_policy';assert r['request_sha256']==sha(native/'agent'/('request-%08d.json'%q['request_id']))
                with torch.no_grad():l,_=models[arm](**collate([q],'cpu'))
                assert int(l[0].argmax())==r['selected_index'];all_replays.append(r['selected_index']);counts['one_move' if sum(c['op']=='move' for c in q['candidates'])==1 else 'multiple_moves']+=1
                counts['stop']+=r['op']=='end_turn'
            all_stop+=counts['stop'];assert len(parsed['sent'])==len(proposals)
            stable=stability(proposals,typed,parsed,128)
            # Bind to real request ID and application interval, never infer ownership from a hero name.
            loglines=(native/'client.log').read_text().splitlines();applies={}
            for number,line in enumerate(loglines,1):
                m=re.search(r'TypedActionApplied player=(\d+) native_request_id=(\d+) op=(move|end_turn) success=([01])',line)
                if m and int(m[1])==pair['job']['player']:applies[int(m[2])]=number
            owned_lines=set();edges=[];matches=[]
            sends={t['decision_id']:t for t in typed if t['event']=='native_action_sent' and t.get('decision_id') is not None}
            for proposal in proposals:
                q=proposal['request'];r=proposal['response']
                if r['op']!='move':continue
                sent=sends[q['request_id']];start=parsed['sent'][q['request_id']];end=applies[sent['native_request_id']]
                origin=list(q['from']);dest=list(q['candidates'][r['selected_index']]['next']);origin[0]+=1;dest[0]+=1
                found=[m for m in parsed['movements'] if start<m['line']<end and m['start']==origin and m['end']==dest]
                assert len(found)==1,(i,arm,q['request_id'],len(found))
                m=found[0];owned_lines.add(m['line']);edges.append(tuple(m['start']+m['end']));matches.append(dict(decision_id=q['request_id'],native_request_id=sent['native_request_id'],line=m['line'],hero=q['hero'],hero_log_name=m['hero_log_name']))
            ec=collections.Counter(edges)
            stable['real_server_owned_movement_count']=len(edges);stable['real_server_repeated_directed_edges']=sum(n-1 for n in ec.values());stable['most_repeated_real_server_edges']=[dict(edge=e,count=n) for e,n in ec.most_common(6)]
            actions=[policy_action(p) for p in proposals]
            arm_summary=dict(win=terminal[0]['event']=='victory',terminal_day=terminal[0]['day'],own_turn=terminal[0]['own_turn'],policy_decisions=len(proposals),counts=dict(counts),native_counts=proof['counts'],stability=stable)
            assert arm_summary['win']==pair['arms'][arm]['win']
            stable['hero_ID_counts']=dict(collections.Counter(p['request']['hero'] for p in proposals));stable['owned_movement_request_bindings']=matches
            arms[arm]=arm_summary;data[arm]=(proposals,parsed,actions,native,owned_lines)
            paths += [native/'PLAN.json',native/'EXECUTION.json',native/'client.log',native/'typed.jsonl',native/'strategy-trace.jsonl',native/'agent/typed-broker.jsonl',target/'raw-audit/AUDIT.json']
        a,pa,aa,na,owned_a=data['a'];b,pb,ab,nb,owned_b=data['b'];requests_a=[x['request'] for x in a];requests_b=[x['request'] for x in b];choices_a=[x['response']['selected_index'] for x in a];choices_b=[x['response']['selected_index'] for x in b]
        first_req=short_diff(requests_a,requests_b);first_choice=short_diff(choices_a,choices_b);first_action=short_diff(aa,ab)
        sameobs_diff=[]
        for k in range(min(len(a),len(b))):
            if requests_a[k]==requests_b[k] and choices_a[k]!=choices_b[k]:sameobs_diff.append(k+1)
        diagnostics=dict(first_request_difference=first_req,first_index_choice_difference=first_choice,first_semantic_action_difference=first_action,same_observation_different_choices=sameobs_diff,full_movement_projection=movement_comparison(pa['movements'],pb['movements']))
        if first_choice:
            k=first_choice['index']-1
            if k<len(a) and k<len(b):
                qa,qb=requests_a[k],requests_b[k];line_a=pa['sent'][qa['request_id']];line_b=pb['sent'][qb['request_id']]
                prefix_a=[x for x in pa['movements'] if x['line']<line_a];prefix_b=[x for x in pb['movements'] if x['line']<line_b]
                npc_a=[x for x in prefix_a if x['line'] not in owned_a];npc_b=[x for x in prefix_b if x['line'] not in owned_b]
                diagnostics['before_first_choice_difference']=dict(decision_index=k+1,a_actual_send_line=line_a,b_actual_send_line=line_b,observations_exact=qa==qb,server_movements=movement_comparison(prefix_a,prefix_b),NPC_movements=movement_comparison(npc_a,npc_b),a_request=qa,b_request=qb,a_action=aa[k],b_action=ab[k])
                replay=[]
                for label,q in [('a_observation',qa),('b_observation',qb)]:
                    with torch.no_grad():x,_=models['a'](**collate([q],'cpu'));y,_=models['b'](**collate([q],'cpu'))
                    x=x[0];y=y[0];replay.append(dict(observation=label,initial_argmax=int(x.argmax()),trained_argmax=int(y.argmax()),initial_top2=x.topk(min(2,len(x))).values.tolist(),trained_top2=y.topk(min(2,len(y))).values.tolist()))
                diagnostics['first_choice_cross_policy_replay']=replay
        paths_pair=OUT/f'pair-{i:02d}/DIAGNOSIS.json';detail=dict(pair=i,job=pair['job'],arms=arms,diagnostics=diagnostics)
        paths_pair.write_text(json.dumps(detail,indent=2)+'\n');paths.append(paths_pair)
        pairs.append(dict(pair=i,job=pair['job'],arms={arm:{k:v for k,v in arms[arm].items() if k!='stability'} for arm in arms},first_request_difference=first_req,first_choice_difference=first_choice,win_delta=int(arms['b']['win'])-int(arms['a']['win']),diagnosis_sha256=sha(paths_pair)))
    assert all_stop==0 and all(p['win_delta']==0 for p in pairs)
    out=dict(passed=True,scope='Independent CPU source/raw replay and recorded movement/action diagnosis, not full world determinism',new_native_games=0,GPU_operations=0,optimizer_steps=0,raw_games_independently_reaudited=16,CPU_argmax_replayed_all_proposals=True,
        baseline_wins=sum(p['arms']['a']['win'] for p in pairs),candidate_wins=sum(p['arms']['b']['win'] for p in pairs),net_wins=sum(p['win_delta'] for p in pairs),argmax_end_turns=all_stop,pairs=pairs,ability_improvement_claim=False,input_sha256={str(p):sha(p) for p in paths})
    (OUT/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('pairs','input_sha256')}))
if __name__=='__main__':main()
