"""New architecture epoch; no schema4 loading relaxation."""
import importlib.util
from pathlib import Path
import torch
from torch import nn
_spec=importlib.util.spec_from_file_location('_learned_build_encoder',Path(__file__).with_name('encoder.py'))
encoder=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(encoder)
STATE_DIM,CANDIDATE_DIM=encoder.STATE_DIM,encoder.CANDIDATE_DIM
ENCODER_VERSION=encoder.ENCODER_VERSION

class PriorCandidateActorCritic(nn.Module):
    def __init__(self,hidden=64,prior_scale=32.,prior_feature_index=13,stop_bias=-2.):
        super().__init__()
        if type(hidden) is not int or hidden<1 or prior_feature_index!=13: raise ValueError('Invalid architecture configuration')
        if not all(torch.isfinite(torch.tensor(float(x))) for x in (prior_scale,stop_bias)) or prior_scale<=0: raise ValueError('Invalid prior')
        self.hidden,self.prior_feature_index=hidden,prior_feature_index
        self.register_buffer('prior_scale',torch.tensor(float(prior_scale)))
        def network(): return nn.Sequential(nn.Linear(STATE_DIM+CANDIDATE_DIM,hidden),nn.Tanh(),nn.Linear(hidden,hidden),nn.Tanh(),nn.Linear(hidden,1))
        self.actor,self.critic=network(),network()
        self.actor.register_parameter('stop_bias',nn.Parameter(torch.tensor(float(stop_bias))))
        nn.init.zeros_(self.actor[-1].weight);nn.init.zeros_(self.actor[-1].bias)

    def forward(self,state,candidates,mask):
        if (candidates.ndim!=3 or candidates.shape[0]<1 or candidates.shape[-1]!=CANDIDATE_DIM
                or state.shape!=(candidates.shape[0],STATE_DIM) or mask.dtype!=torch.bool or mask.shape!=candidates.shape[:2]
                or not bool(mask.any(1).all())): raise ValueError('Invalid schema5 batch/mask')
        if not bool(torch.isfinite(state).all()) or not bool(torch.isfinite(candidates[mask]).all()): raise ValueError('Nonfinite feature')
        clean=torch.where(mask[...,None],candidates,torch.zeros_like(candidates)); bits=clean[...,40:43][mask]
        if not bool(((bits==0)|(bits==1)).all()) or not bool((bits.sum(-1)==1).all()): raise ValueError('Legal op must be three-way onehot')
        move=mask&(clean[...,40]==1); stop=mask&(clean[...,41]==1); build=mask&(clean[...,42]==1)
        if (bool((clean[stop][:,:40]!=0).any()) or bool((clean[build][:,:23]!=0).any())
                or bool((clean[move][:,23:40]!=0).any()) or not bool((state[:,26]==1).all())
                or not bool(((state[:,-1]==0)|(state[:,-1]==1)).all())): raise ValueError('Operation payload contamination')
        if bool(build.any()) and (not bool((state[:,-1,None].expand_as(mask)[build]==1).all())
                or not bool((clean[build][:,23:37]>=0).all())
                or not bool((clean[build][:,30:37]<=1).all())): raise ValueError('Invalid build feature/window')
        category=clean[build][:,37:40]
        if not bool(((category==0)|(category==1)).all()) or not bool((category.sum(-1)==1).all()): raise ValueError('Build category must be onehot')
        joined=torch.cat((state[:,None,:].expand(-1,candidates.shape[1],-1),clean),-1)
        logits=self.actor(joined).squeeze(-1)+self.prior_scale*clean[...,13]*clean[...,40]+self.actor.stop_bias*clean[...,41]
        logits=logits.masked_fill(~mask,-torch.inf)
        pooled=clean.sum(1)/mask.sum(1,keepdim=True)
        value=self.critic(torch.cat((state,pooled),-1)).squeeze(-1)
        return logits,value
