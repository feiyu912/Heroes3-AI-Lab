"""TRAIN-only, common-start actor/value gradient geometry; never updates weights."""
import argparse,hashlib,json,math,sys
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;NATIVE=HERE.parent/'battle-terminal-credit-native-20261023'
sys.path[:0]=[str(NATIVE),str(ROOT/'research'),'/root/heroes3-ai-lab/src/gym']
import full_graph_policy as graph
import restore_learner as restore
from masked_ppo import distribution
SOURCE=Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01/candidate-micro')
TARGETS=HERE.parent/'battle-observed-MC-probe-20261024/MC_TARGETS.pt'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(2);assert not torch.cuda.is_initialized()
    parent=SOURCE/'update-61.pt';assert sha(parent)=='4725dab0332ad93f3806084ce1fc01803e77f5e5ee6ca861d452b63892062840'
    targets=torch.load(TARGETS,map_location='cpu',weights_only=False);prefix=torch.load(SOURCE/'phase-0/admitted-1.pt',map_location='cpu',weights_only=False)
    assert prefix['behavior_checkpoint_sha256']==targets['behavior_sha256']==sha(parent)
    with torch.random.fork_rng(devices=[]):model=graph.FullGraphPair(parent,'last').cpu().eval()
    before=restore.digest(model.state_dict());rng=torch.get_rng_state().clone()
    named=[(name,p) for name,p in model.named_parameters() if p.requires_grad and 'policy_head__' not in name and 'value_head__' not in name]
    assert named;parameters=[p for _,p in named];rows=[]
    old=torch.tensor(prefix['raw']['old_logp']);actions=torch.tensor(prefix['raw']['actions']);observations=prefix['raw']['samples'];assert len(observations)==512
    for target in ('reference','mc'):
        adv=torch.as_tensor(targets[target+'_advantages'].reshape(-1));adv=(adv-adv.mean())/adv.std(unbiased=False).clamp_min(1e-8);returns=torch.as_tensor(targets[target+'_returns'].reshape(-1))
        for start in range(0,512,16):
            batch=graph.collate(observations[start:start+16],'cpu');logits,values=model(*batch);dist=distribution(logits,batch[-1]);logp=dist.log_prob(actions[start:start+16]);ratio=(logp-old[start:start+16]).exp()
            assert float((logp-old[start:start+16]).abs().max().detach())<2e-4
            actor=-torch.minimum(ratio*adv[start:start+16],ratio.clamp(.8,1.2)*adv[start:start+16]).mean()-.005*dist.entropy().mean()
            critic=.5*((values-returns[start:start+16])**2).mean()
            ga=torch.autograd.grad(actor,parameters,retain_graph=True,allow_unused=True)
            gv=torch.autograd.grad(critic,parameters,allow_unused=True)
            for role in ('attacker','defender'):
                aa=vv=dot=0.;used=0
                for (name,_),g,h in zip(named,ga,gv):
                    if not name.startswith('models.'+role+'.'):continue
                    if g is not None:aa+=float(g.double().square().sum());used+=1
                    if h is not None:vv+=float(h.double().square().sum())
                    if g is not None and h is not None:dot+=float((g.double()*h.double()).sum())
                rows.append(dict(target=target,native_tick_batch=start//16,role=role,body_tensors=used,actor_entropy_gradient_norm=math.sqrt(aa),weighted_value_gradient_norm=math.sqrt(vv),value_to_actor_norm_ratio=math.sqrt(vv/aa) if aa else None,cosine=dot/math.sqrt(aa*vv) if aa and vv else None,opposing=dot<0,actor_loss=float(actor.detach()),weighted_value_loss=float(critic.detach())))
            (a.out/'PROGRESS.json').write_text(json.dumps(dict(target=target,rows=start+16,optimizer_steps=0)))
    assert restore.digest(model.state_dict())==before and torch.equal(rng,torch.get_rng_state()) and all(p.grad is None for p in model.parameters()) and not torch.cuda.is_initialized()
    summaries={}
    for target in ('reference','mc'):
        for role in ('attacker','defender'):
            r=[x for x in rows if x['target']==target and x['role']==role];valid=[x for x in r if x['cosine'] is not None]
            summaries[target+'/'+role]=dict(batches=len(r),opposing_batches=sum(x['opposing'] for x in r),mean_cosine=sum(x['cosine'] for x in valid)/len(valid),mean_value_to_actor_norm_ratio=sum(x['value_to_actor_norm_ratio'] for x in valid)/len(valid))
    report=dict(passed=True,common_parent_sha256=sha(parent),target_sha256=sha(TARGETS),summaries=summaries,rows=rows,model_unchanged=True,CPU_RNG_unchanged=True,new_native_games=0,GPU_operations=0,optimizer_steps=0,DEV_rows_used=0,expert_labels=0,scope='Fixed chronological16-row TRAIN groups at common theta61, before optimizer/clip. This is not the actual shuffled PPO gradient path, a causal failure proof, or a new training update.')
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
if __name__=='__main__':main()
