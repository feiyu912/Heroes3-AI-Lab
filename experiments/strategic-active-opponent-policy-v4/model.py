"""CPU-review schema6 extension; manual recruit prior is not learned expertise."""
import hashlib
import importlib.util
from pathlib import Path
import torch
from torch import nn

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_recruit_draft_encoder',HERE/'encoder.py')
encoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(encoder)
PARENT=HERE.parent/'strategic-learned-build-exploration-v1/model.py'
if hashlib.sha256(PARENT.read_bytes()).hexdigest()!='893c045f9787a1afbe1fe32de6205f947da4e045220969dcd68b0d664e3e6700':
    raise RuntimeError('Frozen architecture changed')
spec=importlib.util.spec_from_file_location('_recruit_draft_parent',PARENT)
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
STATE_DIM,CANDIDATE_DIM=encoder.STATE_DIM,encoder.CANDIDATE_DIM
ENCODER_VERSION=encoder.ENCODER_VERSION
ARCHITECTURE_VERSION='schema6-recruit-zero-residual-v2'
EPOCH='strategic-active-opponent-paired-learning-v1'

class PriorCandidateActorCritic(parent.PriorCandidateActorCritic):
    def __init__(self,hidden=64,prior_scale=32.,prior_feature_index=13,stop_bias=-2.,build_bias=0.,recruit_bias=0.,catalog_size=0):
        super().__init__(hidden,prior_scale,prior_feature_index,stop_bias,build_bias)
        if not torch.isfinite(torch.tensor(float(recruit_bias))):raise ValueError('Finite manual recruit prior required')
        self.actor.register_parameter('recruit_bias',nn.Parameter(torch.tensor(float(recruit_bias))))
        if type(catalog_size) is not int or not 0<=catalog_size<=16384:raise ValueError('Invalid catalog size')
        self.catalog_size=catalog_size;self.extra_dim=encoder.EXTRA_DIM+catalog_size;self.candidate_dim=43+self.extra_dim
        self.recruit_actor=nn.Linear(self.extra_dim,1,bias=False)
        self.recruit_critic=nn.Linear(self.extra_dim,1,bias=False)
        nn.init.zeros_(self.recruit_actor.weight);nn.init.zeros_(self.recruit_critic.weight)

    def forward(self,state,candidates,mask):
        if (candidates.ndim!=3 or candidates.shape[0]<1 or candidates.shape[-1]!=self.candidate_dim
                or state.shape!=(candidates.shape[0],STATE_DIM) or mask.dtype!=torch.bool or mask.shape!=candidates.shape[:2]
                or not bool(mask.any(1).all())):raise ValueError('Invalid schema6 batch')
        if not bool(torch.isfinite(state).all()) or not bool(torch.isfinite(candidates[mask]).all()):raise ValueError('Nonfinite features')
        clean=torch.where(mask[...,None],candidates,torch.zeros_like(candidates))
        bits=clean[...,40:44][mask]
        if not bool(((bits==0)|(bits==1)).all()) or not bool((bits.sum(-1)==1).all()):raise ValueError('Four-way op onehot required')
        recruit=mask&(clean[...,43]==1)
        if bool((clean[~recruit&mask][:,43:]!=0).any()):raise ValueError('Recruit features contaminate legacy op')
        # Delegate all original strict numerical checks to the frozen forward. A
        # temporary build representation is ONLY a feature validator, never an action.
        check=clean[...,:43].clone()
        if bool(recruit.any()):
            if bool((clean[recruit][:,:23]!=0).any()) or bool((clean[recruit][:,37:43]!=0).any()):raise ValueError('Recruit move/build payload contamination')
            check[...,42]=torch.where(recruit,torch.ones_like(check[...,42]),check[...,42])
            check[...,39]=torch.where(recruit,torch.ones_like(check[...,39]),check[...,39])
            extras=clean[recruit][:,43:]
            if not bool((extras>=0).all()) or bool((extras[:,4:6]>1).any()):raise ValueError('Invalid recruit fractions')
            for start,end in ((6,9),(9,11),(11,19),(19,26),(33,self.extra_dim)):
                onehot=extras[:,start:end]
                if not bool(((onehot==0)|(onehot==1)).all()) or not bool((onehot.sum(-1)==1).all()):raise ValueError('Invalid recruit categorical')
        parent.PriorCandidateActorCritic.forward(self,state,check,mask)
        base=clean[...,:43];extra=clean[...,43:]
        joined=torch.cat((state[:,None,:].expand(-1,candidates.shape[1],-1),base),-1)
        logits=self.actor(joined).squeeze(-1)+self.prior_scale*base[...,13]*base[...,40]+self.actor.stop_bias*base[...,41]
        logits=logits+self.actor.build_bias*base[...,42]
        logits=logits+self.actor.recruit_bias*extra[...,0]+self.recruit_actor(extra).squeeze(-1)
        pooled=base.sum(1)/mask.sum(1,keepdim=True)
        value=self.critic(torch.cat((state,pooled),-1)).squeeze(-1)
        value=value+self.recruit_critic(extra.sum(1)/mask.sum(1,keepdim=True)).squeeze(-1)
        return logits.masked_fill(~mask,-torch.inf),value

def migrate_weights_only(old_model,manual_recruit_bias=0.,catalog_size=0):
    """In-memory only. New optimizer/RNG/rollout epoch required; no saved model."""
    new=PriorCandidateActorCritic(hidden=old_model.hidden,prior_scale=float(old_model.prior_scale),
        prior_feature_index=old_model.prior_feature_index,stop_bias=float(old_model.actor.stop_bias.detach()),
        build_bias=float(old_model.actor.build_bias.detach()),recruit_bias=manual_recruit_bias,catalog_size=catalog_size)
    missing,unexpected=new.load_state_dict(old_model.state_dict(),strict=False)
    if set(missing)!={'actor.recruit_bias','recruit_actor.weight','recruit_critic.weight'} or unexpected:
        raise ValueError('Unexpected migration state keys')
    return new
