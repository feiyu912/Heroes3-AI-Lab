"""Read-only choice/provenance analysis of all preregistered DEV pairs."""
import json,statistics
from pathlib import Path
import torch
from model_io import load_model
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations/typed-curriculum-paired-dev-02')
torch.set_num_threads(1)
baseline,_,_=load_model(HERE/'cuda-update-engineering-01/update-1.pt','cpu')
candidate,_,_=load_model(HERE/'cuda-curriculum-ack-01/update-1.pt','cpu')
from episode_balanced_ppo import collate
def read(p):return [json.loads(s) for s in p.read_text().splitlines()]
def effect(p):
    q,r=p['request'],p['response'];c=q['candidates'][r['selected_index']]
    return (q['day'],q['own_turn'],q['hero'],r['op'],c.get('kind'),c.get('position'),c.get('next'))
result=json.loads((ROOT/'RESULT.json').read_text());assert result['passed']
pairs=[];stop_gaps=[];centered_changes=[];controlled_differences=0;rows_total=0
for pair in result['pairs']:
    i=pair['pair'];a=ROOT/f'pair-{i:02d}/a/native';b=ROOT/f'pair-{i:02d}/b/native'
    pa=read(a/'agent/typed-broker.jsonl');pb=read(b/'agent/typed-broker.jsonl')
    choice_diff=next((j for j,(x,y) in enumerate(zip(pa,pb)) if effect(x)!=effect(y)),None)
    request_diff=next((j for j in range(min(len(pa),len(pb))) if (a/f'agent/request-{j+1:08d}.json').read_bytes()!=(b/f'agent/request-{j+1:08d}.json').read_bytes()),None)
    states_a=read(a/'strategy-trace.jsonl');states_b=read(b/'strategy-trace.jsonl')
    ending_a=next(r for r in states_a if r['event'] in ('victory','defeat'));ending_b=next(r for r in states_b if r['event'] in ('victory','defeat'))
    entry=dict(pair=i,win_delta=pair['win_delta'],baseline_decisions=len(pa),candidate_decisions=len(pb),
        first_choice_difference=None if choice_diff is None else choice_diff+1,first_request_difference=None if request_diff is None else request_diff+1,
        initial_world_same=pair['initial_request_exact'],baseline_terminal_day=ending_a['day'],candidate_terminal_day=ending_b['day'])
    if choice_diff is not None:
        entry['first_choice_same_request']=pa[choice_diff]['request']==pb[choice_diff]['request']
        entry['request_diverged_before_choice']=request_diff is not None and request_diff<choice_diff
        entry['baseline_first_different_candidate']=pa[choice_diff]['request']['candidates'][pa[choice_diff]['response']['selected_index']]
        entry['candidate_first_different_candidate']=pb[choice_diff]['request']['candidates'][pb[choice_diff]['response']['selected_index']]
        entry['first_choice_day']=pa[choice_diff]['request']['day']
    pairs.append(entry)
    # Same baseline observations under both frozen CPU policies, singleton batch
    # shape exactly matching the evaluator. This is sensitivity, not an extra game.
    for old in pa:
        q=old['request'];inputs=collate([q],'cpu')
        with torch.no_grad():la,_=baseline(**inputs);lb,_=candidate(**inputs)
        n=len(q['candidates']);la=la[0,:n];lb=lb[0,:n]
        assert int(la.argmax())==old['response']['selected_index']
        controlled_differences+=int(la.argmax()!=lb.argmax());rows_total+=1
        centered_changes.append(float(((lb-lb[0])-(la-la[0])).abs().max()))
        stop=next(j for j,c in enumerate(q['candidates']) if c['op']=='end_turn')
        move=[j for j,c in enumerate(q['candidates']) if c['op']=='move']
        if move:stop_gaps.append(float(lb[move].max()-lb[stop]))
out=HERE/'paired-choice-analysis-01';out.mkdir(exist_ok=False)
report=dict(passed=True,baseline_wins=result['baseline_wins'],candidate_wins=result['candidate_wins'],net_wins=result['net_wins'],
    pairs=pairs,baseline_observations_replayed=rows_total,changed_argmax_on_baseline_observations=controlled_differences,
    max_centered_logit_change=max(centered_changes),median_centered_logit_change=statistics.median(centered_changes),
    candidate_move_minus_stop_gap_min=min(stop_gaps),candidate_move_minus_stop_gap_median=statistics.median(stop_gaps),
    actual_policy_EndTurns_in_eval=sum(p['arms'][arm]['counts']['policy_end_turns'] for p in result['pairs'] for arm in ('a','b')),
    new_native_games=0,optimizer_steps=0,interpretation='Small positive DEV paired signal only. No claim of learning human tactics, strategic waiting, general superiority or final-test performance.')
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
