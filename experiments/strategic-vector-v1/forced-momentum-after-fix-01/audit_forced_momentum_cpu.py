#!/usr/bin/env python3
"""Probe inherited Adam momentum on forced-only batches; CPU synthetic only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import torch
from torch.distributions import Categorical

import episode_balanced_ppo as ppo
from verify_episode_balanced_cpu import manifest
from encoder import collate
from model import load_checkpoint


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    torch.random.default_generator.manual_seed(2026101841)
    base=Path(__file__).resolve().parent.parent/'strategic-policy-v2'
    model=load_checkpoint(base/'checkpoints/threat-supply-initial-v3.pt')
    observation=json.loads((base/'fixtures/visible-request.json').read_text())
    rows=[]
    for identity,action,reward in [('A',0,1.),('B',1,-1.)]:
        with torch.no_grad():
            logits,value=model(**collate([observation]))
            logprob=float(Categorical(logits=logits).log_prob(torch.tensor([action]))[0])
        rows.append(dict(episode_id=identity,request=copy.deepcopy(observation),action=action,
                         old_logprob=logprob,old_value=float(value[0]),**{'return':reward}))
    optimizer=torch.optim.Adam(model.parameters(),lr=.0003)
    warmup=ppo.ppo_update(model,optimizer,rows,torch.device('cpu'),episodes=manifest(rows),epochs=1,minibatch_size=2)
    momentum=max(float(optimizer.state[parameter]['exp_avg'].abs().max())
                 for name,parameter in model.named_parameters() if name.startswith('actor.'))
    assert momentum>0
    forced_observation=copy.deepcopy(observation)
    forced_observation['candidates']=forced_observation['candidates'][:1]
    with torch.no_grad():
        _,value=model(**collate([forced_observation]))
    forced=[dict(episode_id='forced',request=forced_observation,action=0,old_logprob=0.,
                 old_value=float(value[0]),**{'return':1.})]
    before=ppo.parameter_snapshot(model)
    before_actor_steps=[int(optimizer.state[parameter]['step'])
                        for name,parameter in model.named_parameters() if name.startswith('actor.')]
    metrics=ppo.ppo_update(model,optimizer,forced,torch.device('cpu'),episodes=manifest(forced),epochs=1,minibatch_size=1)
    actual=ppo.parameter_delta(model,before)
    after_actor_steps=[int(optimizer.state[parameter]['step'])
                       for name,parameter in model.named_parameters() if name.startswith('actor.')]
    report=dict(synthetic_only=True,game_started=False,GPU_initialized=torch.cuda.is_initialized(),
        module_sha256=hashlib.sha256(Path(ppo.__file__).read_bytes()).hexdigest(),
        warmup_actual_optimizer_steps=warmup['optimizer_steps'],actor_momentum_max_abs=momentum,
        forced_actor_objective=metrics['full_batch_post_epoch']['actor'],
        forced_actor_changed=actual['actor']['changed_tensors']>0,
        forced_actual_parameter_delta=actual,before_actor_steps=before_actor_steps,after_actor_steps=after_actor_steps,
        forced_metrics=metrics)
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2))
    (args.out/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key:report[key] for key in ('module_sha256','actor_momentum_max_abs','forced_actor_objective',
        'forced_actor_changed','forced_actual_parameter_delta','before_actor_steps','after_actor_steps')},indent=2))


if __name__=='__main__':
    main()
