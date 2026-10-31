"""One independent trainable build-logit offset over the frozen schema5 model."""
import hashlib,importlib.util
from pathlib import Path
import torch
from torch import nn
PARENT_PATH=Path(__file__).resolve().parent.parent/'strategic-learned-economy-policy-v1/model.py'
PARENT_SHA='80e78ae216394baa1e7437a39b1fd491c2fa91d9efcdc520778b76945456bb76'
if hashlib.sha256(PARENT_PATH.read_bytes()).hexdigest()!=PARENT_SHA:raise RuntimeError('Frozen parent architecture changed')
spec=importlib.util.spec_from_file_location('_build_exploration_parent_model',PARENT_PATH)
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
encoder=parent.encoder
STATE_DIM,CANDIDATE_DIM,ENCODER_VERSION=parent.STATE_DIM,parent.CANDIDATE_DIM,parent.ENCODER_VERSION
ARCHITECTURE_VERSION='schema5-build-logit-offset-v1'
EPOCH='strategic-learned-build-exploration-v1'

class PriorCandidateActorCritic(parent.PriorCandidateActorCritic):
    def __init__(self,hidden=64,prior_scale=32.,prior_feature_index=13,stop_bias=-2.,build_bias=0.):
        super().__init__(hidden,prior_scale,prior_feature_index,stop_bias)
        if not torch.isfinite(torch.tensor(float(build_bias))):raise ValueError('Finite build bias required')
        self.actor.register_parameter('build_bias',nn.Parameter(torch.tensor(float(build_bias))))

    def forward(self,state,candidates,mask):
        logits,value=super().forward(state,candidates,mask)
        build=mask&(candidates[...,42]==1.)
        return logits+self.actor.build_bias*build.to(logits.dtype),value
