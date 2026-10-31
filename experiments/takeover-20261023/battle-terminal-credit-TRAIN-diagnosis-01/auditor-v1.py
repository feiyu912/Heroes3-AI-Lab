"""Read existing .95 candidate TRAIN only: outcomes, margins and terminal-credit attenuation."""
import argparse,collections,hashlib,json,sys
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent
sys.path[:0]=[str(ROOT/'research'),'/root/heroes3-ai-lab/src/gym']
import full_graph_policy as graph
from masked_ppo import gae
OLD=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01')
RUN=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-01')
KEYS=['reward','value','next_value','terminal','truncated']
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def payload(p):return torch.load(p,map_location='cpu',weights_only=False)
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);assert not torch.cuda.is_initialized()
    assert read(RUN/'RESULT.json')['passed'] and read(HERE/'terminal-credit-delivery-01/AUDIT.json')['passed']
    frozen=read(RUN/'FREEZE.json')['input_sha256'];assert all(sha(p)==h for p,h in frozen.items())
    groups={};fragments=[];inputs={};aliases=[]
    for phase in range(4):
        stage=OLD/'candidate-micro' if phase==0 else RUN/f'candidate-phase-{phase}'
        assert read(stage/'RESULT.json')['passed'] and read(stage/'AUDIT.json')['passed']
        folder=stage/f'phase-{phase}';cfg=read(folder/'WORKERS.json')['configs'];assert len(cfg)==16
        lengths=[0]*16;parts={}
        for part,count in [('admitted-0',32),('admitted-1',32),('suffix',64)]:
            path=folder/(part+'.pt');data=payload(path);inputs[str(path)]=sha(path);parts[part]=data
            assert len(data['journal'])==count*2 and data['suffix_private_RNG']==(part=='suffix')
            for tick in range(count):
                pair=[]
                for item in data['journal'][tick*2:tick*2+2]:
                    current=folder/Path(item['path']).name;actual=sha(current);assert actual==item['sha256'];inputs[str(current)]=actual
                    if str(current)!=item['path']:
                        assert sha(item['path'])==actual;aliases.append(dict(current=str(current),reference=item['path'],sha256=actual))
                    pair.append(payload(current))
                decision,returned=pair;assert len(returned['responses'])==len(decision['obs'])==16
                for slot,(obs,response) in enumerate(zip(decision['obs'],returned['responses'])):
                    job=cfg[slot];key=f"{job['opponent']}/family{job['family']}/{part}"
                    g=groups.setdefault(key,dict(rows=0,terminals=0,wins=0,losses=0,truncations=0,free_choices=0,greedy_selections=0,top_probability_sum=0.,entropy_sum=0.,top_margin_sum=0.,completed_episode_steps=[]))
                    n=len(obs['active_action_ids']);scores=decision['logits'][slot,:n];prob=decision['probabilities'][slot,:n]
                    assert n>0 and bool(torch.isfinite(scores).all()) and abs(float(prob.sum())-1)<2e-5
                    g['rows']+=1;g['top_probability_sum']+=float(prob.max());g['entropy_sum']+=float(-(prob*prob.clamp_min(1e-30).log()).sum())
                    g['greedy_selections']+=int(decision['actions'][slot])==int(scores.argmax())
                    if n>1:
                        top=scores.topk(2).values;g['free_choices']+=1;g['top_margin_sum']+=float(top[0]-top[1])
                    lengths[slot]+=1
                    assert response['terminated']==bool(data['arrays']['terminal'][tick,slot]) and response['truncated']==bool(data['arrays']['truncated'][tick,slot])
                    if response['terminated']:
                        outcome=response['outcome'];assert outcome==response['native_step_return']['obs']['terminal_outcome'] and outcome['result_type']==0
                        win=outcome['winner']==obs['lab_side'];assert abs(response['reward']-(1 if win else -1))<1e-7
                        g['terminals']+=1;g['wins']+=win;g['losses']+=not win;g['completed_episode_steps'].append(lengths[slot]);lengths[slot]=0
                    elif response['truncated']:g['truncations']+=1;lengths[slot]=0
        prefix=parts['admitted-1']['arrays'];suffix=parts['suffix']['arrays'];target=payload(folder/'TARGETS.pt')['targets']
        joined={k:np.concatenate([prefix[k],suffix[k]],axis=0) for k in KEYS}
        mc_adv,mc_return=gae(*(joined[k] for k in KEYS),gamma=1.,lam=1.)
        for slot,job in enumerate(cfg):
            if not target['eligible'][slot]:continue
            ended=np.flatnonzero(prefix['terminal'][:,slot]|prefix['truncated'][:,slot]);start=int(ended[-1])+1 if len(ended) else 0
            end=32+int(np.flatnonzero(suffix['terminal'][:,slot]|suffix['truncated'][:,slot])[0])
            assert joined['terminal'][end,slot] and not joined['truncated'][end,slot] and start<32
            expected=[];weights=[];deltas=[]
            for tick in range(start,32):
                ret=float(np.sum(joined['reward'][tick:end+1,slot],dtype=np.float64))
                assert abs(ret-float(mc_return[tick,slot]))<2e-5
                obs=parts['admitted-1']['raw']['samples'][tick*16+slot]
                terminal_reward=ret+.5*graph.potential(obs);assert min(abs(terminal_reward-1),abs(terminal_reward+1))<2e-5
                expected.append(ret);weights.append(.95**(end-tick));deltas.append(float(mc_adv[tick,slot]-target['candidate_advantage'][tick,slot]))
            fragments.append(dict(phase=phase,slot=slot,opponent=job['opponent'],role=job['role'],family=job['family'],scenario=job['TRAIN_scenario_index'],prefix_fragment_start=start,prefix_rows=32-start,first_suffix_terminal_step=end-31,maximum_terminal_distance=end-start,mean_terminal_coefficient_lambda095=float(np.mean(weights)),minimum_terminal_coefficient_lambda095=min(weights),rows_coefficient_below_quarter=sum(w<.25 for w in weights),MC_return_telescopes_to_native_outcome_minus_potential=True,MC_outcome_win=terminal_reward>0,mean_MC_minus_extended095_advantage=float(np.mean(deltas)),max_abs_MC_minus_extended095_advantage=max(abs(x) for x in deltas),raw_advantage_sign_flips=sum(np.sign(mc_adv[t,slot])!=np.sign(target['candidate_advantage'][t,slot]) for t in range(start,32))))
        (a.out/'PROGRESS.json').write_text(json.dumps(dict(phases=phase+1,fragments=len(fragments),new_native_games=0,optimizer_steps=0)))
        del parts
    for g in groups.values():
        g['mean_greedy_probability']=g.pop('top_probability_sum')/g['rows'];g['mean_entropy']=g.pop('entropy_sum')/g['rows'];g['mean_free_choice_top2_margin']=g.pop('top_margin_sum')/max(1,g['free_choices'])
    assert all(sha(p)==h for p,h in inputs.items()) and all(sha(p)==h for p,h in frozen.items()) and not torch.cuda.is_initialized()
    report=dict(passed=True,reference_arm='historical lambda.95 terminal-extension candidate chain; current recovery-01 only',groups=groups,eligible_worker_phase_fragments=len(fragments),fragments=fragments,fragment_rows=sum(f['prefix_rows'] for f in fragments),rows_terminal_coefficient_below_quarter=sum(f['rows_coefficient_below_quarter'] for f in fragments),maximum_terminal_distance=max(f['maximum_terminal_distance'] for f in fragments),all_MC_returns_independently_verified=True,input_sha256=inputs,byte_equal_journal_aliases=aliases,new_native_games=0,neural_forwards=0,GPU_operations=0,optimizer_steps=0,expert_labels=0,DEV_rows_used=0,scope='Descriptive TRAIN observations, not IID evaluation. Episodes may cross policy updates; suffix has zero PPO loss. MC targets are offline hypotheses, not admitted new training.')
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('groups','fragments','input_sha256','byte_equal_journal_aliases')},indent=2))
if __name__=='__main__':main()
