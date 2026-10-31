"""Differentiable graph batches for selective/full fine-tuning of public v15."""
import importlib.util
from pathlib import Path
import numpy as np
import torch
import gc
import time

spec=importlib.util.spec_from_file_location('full_graph_base',Path(__file__).with_name('recovered-graph.py'))
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


def tensors_batch(model,observations):
    device=next(model.parameters()).device
    offsets={n:np.cumsum([0]+[len(o['nodes'][n]) for o in observations]) for n in model.nodes}
    nodes={n:torch.as_tensor(np.concatenate([o['nodes'][n] for o in observations]),device=device) for n in model.nodes}
    edges=[]
    for key in model.edges:
        indices=[];attrs=[]
        for i,obs in enumerate(observations):
            index=obs['edges'][key]['index'].astype(np.int64).copy()
            index[0]+=offsets[key[0]][i];index[1]+=offsets[key[2]][i]
            indices.append(index);attrs.append(obs['edges'][key]['attrs'])
        edges.append((torch.as_tensor(np.concatenate(indices,1),device=device),
            torch.as_tensor(np.concatenate(attrs),device=device)))
    return nodes,edges,offsets


def collate(observations,device='cpu'):
    mask=np.zeros((len(observations),max(len(o['active_action_ids']) for o in observations)),bool)
    for i,obs in enumerate(observations):mask[i,:len(obs['active_action_ids'])]=True
    return observations,torch.as_tensor(mask,device=device)


class FullGraphPair(base.RecoveredPair):
    def __init__(self,checkpoint,mode='last'):
        super().__init__(checkpoint)
        assert mode in ['heads','last','all']
        self.finetuning_mode=mode
        for name,parameter in self.named_parameters():
            parameter.requires_grad_(mode=='all' or 'policy_head__' in name or 'value_head__' in name
                or (mode=='last' and ('gnn__convs__2__' in name or 'gnn__norms__2__' in name)))

    def forward(self,observations,mask):
        device=next(self.parameters()).device
        rows=[None]*len(observations);values=[None]*len(observations)
        for side,role in enumerate(['attacker','defender']):
            indices=[i for i,o in enumerate(observations) if o['lab_side']==side]
            if not indices:continue
            group=[observations[i] for i in indices];model=self.models[role]
            nodes,edges,offsets=tensors_batch(model,group)
            encoded=model.encode(nodes,edges)
            value=model.head(encoded['Global'],'value_head').squeeze(-1)
            for j,i in enumerate(indices):
                action_ids=torch.as_tensor(group[j]['active_action_ids']+offsets['Action'][j],device=device)
                logits=model.head(encoded['Action'][action_ids],'policy_head').squeeze(-1)
                rows[i]=torch.nn.functional.pad(logits,(0,mask.shape[1]-len(logits)),value=-torch.inf)
                values[i]=value[j]
        return torch.stack(rows).masked_fill(~mask,-torch.inf),torch.stack(values)


def potential(obs):
    # Column indices come from the runtime schema, not presumed node ordering.
    from vcmi_gym.envs.v15.vcmi_env import Player
    players=Player.decode_many(obs['nodes']['Player'])
    side=obs['lab_side']
    own=next(p.ARMY_VALUE_NOW_REL0 for p in players if p.BATTLE_SIDE==side)
    enemy=next(p.ARMY_VALUE_NOW_REL0 for p in players if p.BATTLE_SIDE!=side)
    return (own-enemy)/1000.0


def choose_microbatch(model,observations,preferred):
    """Probe gradients without changing weights, optimizer, or sampling RNG."""
    device=next(model.parameters()).device
    versions=[p._version for p in model.parameters()]
    cpu_rng=torch.get_rng_state();cuda_rng=torch.cuda.get_rng_state_all()
    trials=[]
    def probe(size):
        batch=[observations[i%len(observations)] for i in range(size)]
        torch.cuda.synchronize();tick=time.monotonic()
        torch.cuda.reset_peak_memory_stats()
        before=torch.cuda.memory_allocated()
        logits,values=model(*collate(batch,device))
        loss=-logits.log_softmax(-1)[:,0].mean()+values.square().mean()
        assert torch.isfinite(loss)
        loss.backward();torch.cuda.synchronize()
        assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())
        return dict(size=size,seconds=time.monotonic()-tick,
            incremental_allocated_mib=(torch.cuda.memory_allocated()-before)/1024**2,
            peak_reserved_mib=torch.cuda.max_memory_reserved()/1024**2)
    size=preferred
    while size>=2:
        try:
            trial=probe(size);trial['passed']=trial['peak_reserved_mib']<8192
            trials.append(trial)
        except torch.cuda.OutOfMemoryError:
            trials.append(dict(size=size,passed=False,reason='CUDA out of memory'))
        model.zero_grad(set_to_none=True);gc.collect();torch.cuda.empty_cache()
        if trials[-1]['passed']:break
        size//=2
    assert trials[-1]['passed'],'No safe microbatch size'
    assert versions==[p._version for p in model.parameters()]
    assert torch.equal(cpu_rng,torch.get_rng_state())
    assert all(torch.equal(a,b) for a,b in zip(cuda_rng,torch.cuda.get_rng_state_all()))
    return size,dict(trials=trials,weights_unchanged=True,sampling_rng_unchanged=True,optimizer_steps=0)
