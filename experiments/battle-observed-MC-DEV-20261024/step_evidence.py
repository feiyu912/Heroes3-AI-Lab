"""Append-only per-decision evidence; no native or GPU operations."""
import hashlib,json,os
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,payload):
    import torch
    path=Path(path);assert not path.exists();tmp=path.with_suffix(path.suffix+'.tmp')
    assert not tmp.exists();torch.save(payload,tmp);os.replace(tmp,path)
    return dict(path=str(path),sha256=sha(path),bytes=path.stat().st_size)
class Journal:
    def __init__(self,path,identity):
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=False);self.identity=identity;self.files=[];self.decisions=0;self.transitions=0
    def decision(self,obs,logits,value,action):
        import numpy as np
        import torch
        ids=np.asarray(obs['active_action_ids']);scores=logits.detach().cpu().reshape(-1)
        assert scores.numel()==len(ids) and bool(torch.isfinite(scores).all()) and bool(torch.isfinite(value).all()) and int(action) in ids
        assert int(ids[int(scores.argmax())])==action
        assert self.decisions==self.transitions
        self.decisions+=1
        p=self.path/f'decision-{self.decisions:06d}.pt'
        item=save(p,dict(schema='battle-policy-decision-v1',identity=self.identity,step=self.decisions,obs=obs,
            active_action_ids=ids.copy(),logits=scores,probabilities=torch.softmax(scores,dim=-1),value=value.detach().cpu(),action=int(action),selection='argmax'))
        self.files.append(item);return item
    def transition(self,obs,reward,terminated,truncated,info):
        assert self.decisions==self.transitions+1
        self.transitions+=1;p=self.path/f'transition-{self.transitions:06d}.pt'
        item=save(p,dict(schema='battle-native-step-return-v1',identity=self.identity,step=self.transitions,next_obs=obs,
            reward=float(reward),terminated=bool(terminated),truncated=bool(truncated),info=info,
            meaning='Actual synchronous native env.step return; not a fabricated separate server ACK'))
        self.files.append(item);return item
    def manifest(self,complete=False):
        assert not complete or self.decisions==self.transitions
        return dict(schema='battle-step-evidence-v1',path=str(self.path),identity=self.identity,complete=bool(complete),decisions=self.decisions,
            native_step_returns=self.transitions,files=self.files,unreturned_decision=self.decisions-self.transitions)
