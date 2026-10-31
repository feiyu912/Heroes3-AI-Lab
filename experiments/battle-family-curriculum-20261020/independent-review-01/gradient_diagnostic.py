"""Actual first TRAIN rollout gradient decomposition, CPU autograd only, no optimizer."""
import hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
import torch
OUT=Path(__file__).resolve().parent;HERE=OUT.parent;R=HERE.parent.parent/'research';LAB=Path('/root/heroes3-ai-lab');B=LAB/'evaluations/battle-family-curriculum-native-01'
sys.path.insert(0,str(R))
import full_graph_policy as graph
from masked_ppo import gae,distribution
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stats(left,right,indices):
    aa=bb=ab=total=0.;an=bn=both=coordinates=0
    for i in indices:
        a,b=left[i],right[i]
        if a is not None:aa+=float(a.double().square().sum())
        if b is not None:bb+=float(b.double().square().sum())
        if a is not None and b is not None:ab+=float((a.double()*b.double()).sum())
        a_nonzero=a is not None and bool(a.ne(0).any());b_nonzero=b is not None and bool(b.ne(0).any());an+=a_nonzero;bn+=b_nonzero;both+=a_nonzero and b_nonzero
        if a_nonzero and b_nonzero:coordinates+=int((a.ne(0)&b.ne(0)).sum())
    total=max(0.,aa+bb+2*ab)
    return dict(actor_norm=aa**.5,critic_norm=bb**.5,combined_norm=total**.5,actor_critic_cosine=ab/(aa*bb)**.5 if aa and bb else None,critic_over_actor_norm=(bb/aa)**.5 if aa else None,
        actor_nonzero_tensors=an,critic_nonzero_tensors=bn,both_nonzero_tensors=both,nonzero_coordinate_overlap=coordinates)
def main():
    torch.set_num_threads(1);started=time.monotonic();report=json.loads((B/'training.json').read_text());folder=Path(report['checkpoint']).parent;rp=folder/'rollout-1.pt';raw=torch.load(rp,map_location='cpu',weights_only=False)
    assert len(raw['samples'])==384 and len(raw['configs'])==12
    b64=LAB/'models/graph-finetune/1792068859379237126/update-64.pt';assert sha(b64)=='1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936'
    model=graph.FullGraphPair(str(b64),'last').cpu().eval();before={n:p.detach().clone() for n,p in model.named_parameters()};params=[(n,p) for n,p in model.named_parameters() if p.requires_grad];plist=[p for n,p in params]
    advantage,returns=gae(raw['rewards'],raw['values'],raw['next_values'],raw['terminated'],raw['truncated'],gamma=1.,lam=.95)
    advantages=torch.tensor(advantage.reshape(-1),dtype=torch.float32);advantages=(advantages-advantages.mean())/advantages.std(unbiased=False).clamp(min=1e-8);returns=torch.tensor(returns.reshape(-1),dtype=torch.float32)
    groups={'all':list(range(len(params))),'shared_last_graph':[i for i,(n,p) in enumerate(params) if 'gnn__' in n],
        'policy_heads':[i for i,(n,p) in enumerate(params) if 'policy_head__' in n],'value_heads':[i for i,(n,p) in enumerate(params) if 'value_head__' in n]}
    for role in ('attacker','defender'):
        groups[role+'/shared_last_graph']=[i for i in groups['shared_last_graph'] if role in params[i][0]]
    batches=[]
    for offset in (0,96,192,288):
        indices=list(range(offset,offset+8));obs=[raw['samples'][i] for i in indices];batch=graph.collate(obs,'cpu');logits,value=model(*batch);dist=distribution(logits,batch[-1]);actions=torch.tensor([raw['actions'][i] for i in indices]);old=torch.tensor([raw['old_logp'][i] for i in indices],dtype=torch.float32)
        logp=dist.log_prob(actions);ratio=(logp-old).exp();a=advantages[indices];surrogate=-torch.minimum(ratio*a,ratio.clamp(.8,1.2)*a).mean();entropy=dist.entropy().mean();actor=surrogate-.005*entropy;critic=.5*((value-returns[indices])**2).mean()
        ga=torch.autograd.grad(actor,plist,retain_graph=True,allow_unused=True);gc=torch.autograd.grad(critic,plist,allow_unused=True)
        metrics={name:stats(ga,gc,ids) for name,ids in groups.items()};scale=min(1.,.5/(metrics['all']['combined_norm']+1e-6))
        for m in metrics.values():m['post_global_clip_actor_norm']=m['actor_norm']*scale;m['post_global_clip_critic_norm']=m['critic_norm']*scale
        batches.append(dict(indices=indices,roles=[o['lab_side'] for o in obs],families=[raw['configs'][i%12]['family'] for i in indices],actor_surrogate=float(surrogate.detach()),entropy=float(entropy.detach()),actor_plus_entropy_loss=float(actor.detach()),half_value_loss=float(critic.detach()),
            CPU_selected_logprob_difference_max=float((logp.detach()-old).abs().max()),global_clip_max_norm=.5,global_clip_scale=scale,groups=metrics))
        print(json.dumps(dict(indices=indices,global_clip_scale=scale,shared=metrics['shared_last_graph'],all=metrics['all'])),flush=True)
    assert all(torch.equal(p,before[n]) and p.grad is None for n,p in model.named_parameters())
    out=dict(passed=True,scope='Four preregistered real TRAIN minibatches at pre-update B64. CPU autograd, not full-rollout gradient distribution or actual Adam updates.',new_native_games=0,GPU_operations=0,optimizer_steps=0,model_parameters_unchanged=True,
        sample_source=str(rp),sample_count_in_rollout=384,diagnostic_rows=32,offsets=[0,96,192,288],gamma=1.,gae_lambda=.95,advantage_normalized_over_all_384=True,batches=batches,
        last_graph_group_definition='The shared_last_graph key is only the aggregate of released last-layer graph tensors. Empirical nonzero support overlap is measured separately; this name does not assert the tensors are shared by actor and critic.',
        caveat='Global clipping rescales both contributions equally. Adam per-coordinate moments and learning-rate groups can change update direction/relative step sizes; gradient dominance alone does not establish skill causation.',
        input_sha256={str(p):sha(p) for p in [Path(__file__),rp,b64,B/'training.json',R/'masked_ppo.py',R/'full_graph_policy.py',R/'recovered-graph.py']},elapsed_seconds=time.monotonic()-started)
    (OUT/'GRADIENT_DIAGNOSTIC.json').write_text(json.dumps(out,indent=2)+'\n')
if __name__=='__main__':main()
