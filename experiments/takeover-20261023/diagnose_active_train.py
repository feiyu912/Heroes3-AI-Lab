"""All TRAIN behavior numerics and initial recruit-bias gradient, no optimization."""
import argparse,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'strategic-active-opponent-learning-20261024'
sys.path.insert(0,str(PACKAGE))
from pipeline_common import BASE,DEFAULT_INITIAL,INITIAL_SHA,sha
import torch
from model_io import load_model,tensor_sha
from load_admitted import load
from episode_balanced_ppo import prepare_batch,PROTOCOL
import encoder
def read(p):return json.loads(Path(p).read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    assert read(a.run/'RESULT.json')['passed'] and read(HERE/'active-learning-independent-01/AUDIT.json')['passed']
    torch.set_num_threads(1);model,_,digest=load_model(DEFAULT_INITIAL,'cpu');assert digest==INITIAL_SHA
    before=tensor_sha(model.state_dict());rng=torch.get_rng_state().clone();reports={}
    for arm in ('control','curriculum'):
        samples=[];episodes=[];oldrows=[]
        for i in range(8):
            root=a.run/arm/f'cell-{i:02d}';s,e,_=load(root/'admitted');samples+=s;episodes+=e
            oldrows += [json.loads(line) for line in (root/'native/agent/typed-broker.jsonl').read_text().splitlines()]
        assert len(oldrows)==len(samples)
        prepared=prepare_batch(samples,'cpu',episodes=episodes);size=len(samples);by_episode={e['episode_id']:e['job'] for e in episodes}
        groups={};auto_total=analytic_total=entropy_total=0.;max_logp=max_value=max_class=0.
        for offset in range(0,size,64):
            rows=samples[offset:offset+64];old=oldrows[offset:offset+64]
            batch=encoder.collate([s['request'] for s in rows],'cpu');logits,values=model(**batch)
            logp=logits.log_softmax(-1);prob=logp.exp();safe_logp=torch.where(batch['mask'],logp,torch.zeros_like(logp))
            R=torch.zeros_like(batch['mask']);B=torch.zeros_like(batch['mask'])
            for j,s in enumerate(rows):
                for k,c in enumerate(s['request']['candidates']):R[j,k]=c['op']=='recruit';B[j,k]=c['op']=='build'
            pR=(prob*R).sum(-1);pB=(prob*B).sum(-1)
            acts=torch.tensor([s['action'] for s in rows]);selected=logp.gather(1,acts[:,None]).squeeze(1)
            archived=prepared['old_logprob'][offset:offset+len(rows)];ratio=(selected-archived).exp()
            assert bool(((ratio>.8)&(ratio<1.2)).all()),'Initial clipping unexpected'
            w=prepared['actor_weights'][offset:offset+len(rows)];adv=prepared['advantages'][offset:offset+len(rows)]
            H=-(prob*safe_logp).sum(-1)
            objective=(w*adv*ratio).sum()/size+PROTOCOL['entropy_coefficient']*(w*H).sum()/size
            automatic=float(torch.autograd.grad(objective,model.actor.recruit_bias)[0]);auto_total+=automatic
            selected_R=torch.tensor([s['action_type']=='recruit' for s in rows],dtype=torch.float32)
            pg=w*adv*ratio*(selected_R-pR)/size
            eh=-PROTOCOL['entropy_coefficient']*w*((prob*safe_logp*R).sum(-1)-pR*(prob*safe_logp).sum(-1))/size
            analytical=float((pg+eh).sum());assert abs(automatic-analytical)<1e-6
            analytic_total+=float(pg.sum());entropy_total+=float(eh.sum())
            for j,(s,original) in enumerate(zip(rows,old)):
                assert s['request']==original['request'] and s['action']==original['action'] and s['old_logprob']==original['old_logprob'] and s['old_value']==original['old_value']
                dl=abs(float(selected[j])-s['old_logprob']);dv=abs(float(values[j])-s['old_value'])
                dc=max(abs(float(pR[j])-original['recruit_probability']),abs(float(pB[j])-original['build_probability']))
                assert dl<=2e-5+1e-5*abs(s['old_logprob']) and dv<=2e-5+1e-5*abs(s['old_value']) and dc<=3e-5
                max_logp=max(max_logp,dl);max_value=max(max_value,dv);max_class=max(max_class,dc)
                key=by_episode[s['episode_id']]['opponent']+'/'+s['action_type'];g=groups.setdefault(key,dict(rows=0,negative_advantage=0,positive_advantage=0,initial_recruit_bias_policy_ascent=0.,initial_recruit_bias_entropy_ascent=0.,sum_greedy_action_probability=0.,sum_entropy=0.,sum_recruit_probability=0.,sum_candidate_count=0))
                g['rows']+=1;g['negative_advantage']+=float(adv[j])<0;g['positive_advantage']+=float(adv[j])>0
                g['initial_recruit_bias_policy_ascent']+=float(pg[j].detach());g['initial_recruit_bias_entropy_ascent']+=float(eh[j].detach())
                g['sum_greedy_action_probability']+=float(prob[j].max().detach());g['sum_entropy']+=float(H[j].detach());g['sum_recruit_probability']+=float(pR[j].detach());g['sum_candidate_count']+=len(s['request']['candidates'])
            (a.out/'PROGRESS.json').write_text(json.dumps(dict(arm=arm,rows=min(offset+64,size),optimizer_steps=0)))
        for g in groups.values():
            for key in ('greedy_action_probability','entropy','recruit_probability','candidate_count'):g['mean_'+key]=g.pop('sum_'+key)/g['rows']
        assert abs(auto_total-analytic_total-entropy_total)<1e-5
        trained=read(a.run/arm/'update-01/RESULT.json')
        reports[arm]=dict(rows=size,groups=groups,initial_full_batch_recruit_bias_policy_ascent=analytic_total,initial_full_batch_recruit_bias_entropy_ascent=entropy_total,initial_full_batch_recruit_bias_autograd=auto_total,analytic_autograd_agree=True,CPU_CUDA_archived_selected_logp_max_abs_error=max_logp,CPU_CUDA_archived_value_max_abs_error=max_value,CPU_CUDA_archived_class_probability_max_abs_error=max_class,actual_training_bias_delta=trained['recruit_bias_delta'],actual_training_Adam=trained['cuda_optimizer_steps'],advantage_moments=prepared['metadata'])
        del samples,episodes,oldrows,prepared
    assert tensor_sha(model.state_dict())==before and torch.equal(torch.get_rng_state(),rng) and sha(DEFAULT_INITIAL)==INITIAL_SHA
    report=dict(passed=True,arms=reports,complete_TRAIN_rows_numerically_recomputed=sum(r['rows'] for r in reports.values()),model_unchanged=True,CPU_RNG_unchanged=True,optimizer_steps=0,GPU_operations=0,native_games=0,expert_labels=0,DEV_teacher_rows=0,scope='Initial raw recruit-bias gradient includes unchosen actions and entropy. Full PPO epochs/minibatches/Adam/clipping differ later; this is not causal action quality or a new training update.')
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='arms'},indent=2))
if __name__=='__main__':main()
