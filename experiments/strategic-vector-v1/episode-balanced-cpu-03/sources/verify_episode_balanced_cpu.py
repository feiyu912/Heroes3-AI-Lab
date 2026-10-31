#!/usr/bin/env python3
"""Synthetic CPU objective invariance, actual gradient/update and abort checks."""
import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch

import torch
from torch.distributions import Categorical

import episode_balanced_ppo as ppo
from encoder import collate
from model import load_checkpoint

HERE = Path(__file__).resolve().parent
V2 = HERE.parent/'strategic-policy-v2'


def manifest(rows):
    counts = Counter(row['episode_id'] for row in rows)
    rewards = {row['episode_id']:row['return'] for row in rows}
    return [dict(episode_id=identity,valid=True,reward=rewards[identity],decisions=count,
                 native_consumption_verified=True,native=dict(completed=True,inputs_unchanged=True),SYNTHETIC_ONLY=True)
            for identity,count in counts.items()]


def scalar_terms(model,rows):
    prepared=ppo.prepare_batch(rows,episodes=manifest(rows))
    with torch.no_grad():
        values=ppo.objective_terms(model,rows,prepared)
    return {name:float(value) for name,value in values.items()},prepared


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    torch.random.default_generator.manual_seed(2026101837)
    model=load_checkpoint(V2/'checkpoints/threat-supply-initial-v3.pt')
    request=json.loads((V2/'fixtures/visible-request.json').read_text())
    rows=[]
    for identity,length,free,reward in [('A',3,2,1.),('B',5,4,-1.),('C',2,0,1.)]:
        for index in range(length):
            observation=copy.deepcopy(request)
            observation.update(request_id=index+1,day=index+1)
            if index>=free:
                observation['candidates']=observation['candidates'][:1]
            with torch.no_grad():
                logits,value=model(**collate([observation]))
                action=index%len(observation['candidates'])
                logprob=float(Categorical(logits=logits).log_prob(torch.tensor([action]))[0])
            rows.append(dict(episode_id=identity,request=observation,action=action,old_logprob=logprob,
                             old_value=float(value[0]),**{'return':reward}))
    original,prepared=scalar_terms(model,rows)
    # Add arbitrarily many forced transitions to an existing episode. Its free
    # choice distribution, advantage moments and actor/entropy/KL stay identical.
    forced=next(row for row in rows if row['episode_id']=='A' and len(row['request']['candidates'])==1)
    extended=copy.deepcopy(rows)+[copy.deepcopy(forced) for _ in range(17)]
    extended_terms,extended_prepared=scalar_terms(model,extended)
    for name in ('actor','entropy','kl','conditional_kl'):
        assert abs(original[name]-extended_terms[name])<1e-6,(name,original,extended_terms)
    assert abs(prepared['metadata']['advantage_mean']-extended_prepared['metadata']['advantage_mean'])<1e-7
    assert abs(prepared['metadata']['advantage_variance']-extended_prepared['metadata']['advantage_variance'])<1e-7
    # Repeating every state of just one episode equally leaves its empirical
    # critic distribution unchanged; episode-balanced critic objective is equal.
    repeated=copy.deepcopy(rows)+[copy.deepcopy(row) for _ in range(9) for row in rows if row['episode_id']=='B']
    repeated_terms,_=scalar_terms(model,repeated)
    assert abs(original['critic']-repeated_terms['critic'])<1e-6
    # Each episode has exactly 1/E critic objective mass. A and B each have 1/E
    # actor mass, C has none because it has no free choices.
    objective_mass={}
    for identity in ('A','B','C'):
        indices=[index for index,row in enumerate(rows) if row['episode_id']==identity]
        objective_mass[identity]=dict(actor=float(prepared['actor_weights'][indices].sum()/len(rows)),
                                      critic=float(prepared['critic_weights'][indices].sum()/len(rows)))
    assert abs(objective_mass['A']['actor']-1/3)<1e-7 and objective_mass['C']['actor']==0.
    assert all(abs(value['critic']-1/3)<1e-7 for value in objective_mass.values())
    # Actor gradients, not only scalar loss values, are invariant to added forced
    # rows. Critic gradients are invariant to complete within-episode repetition.
    def gradients(samples,term):
        model.zero_grad(set_to_none=True)
        batch=ppo.prepare_batch(samples,episodes=manifest(samples))
        loss=ppo.objective_terms(model,samples,batch)[term]
        loss.backward()
        prefix='actor.' if term=='actor' else 'critic.'
        return {name:parameter.grad.detach().clone() for name,parameter in model.named_parameters() if name.startswith(prefix)}
    actor_a,actor_b=gradients(rows,'actor'),gradients(extended,'actor')
    critic_a,critic_b=gradients(rows,'critic'),gradients(repeated,'critic')
    actor_gradient_error=max(float((actor_a[name]-actor_b[name]).abs().max()) for name in actor_a)
    critic_gradient_error=max(float((critic_a[name]-critic_b[name]).abs().max()) for name in critic_a)
    assert actor_gradient_error<1e-7 and critic_gradient_error<1e-6
    optimizer=torch.optim.Adam(model.parameters(),lr=.0003)
    progress={}
    metrics=ppo.ppo_update(model,optimizer,rows,torch.device('cpu'),progress,episodes=manifest(rows),epochs=2,minibatch_size=4)
    assert metrics['completed'] and metrics['optimizer_steps']==ppo.optimizer_steps(optimizer)==6
    assert all(metrics['parameter_delta_from_previous_update'][group]['changed_tensors']>0 for group in ('actor','critic'))
    successful=copy.deepcopy(metrics)
    # Failures must be rejected before a single optimizer state advance.
    invalid_cases=[]
    bad=copy.deepcopy(rows);bad[0]['return']=None
    invalid_cases.append((bad,manifest(rows)))
    bad=copy.deepcopy(rows);bad[0].pop('episode_id')
    invalid_cases.append((bad,manifest(rows)))
    bad_manifest=manifest(rows);bad_manifest[0]['valid']=False
    invalid_cases.append((rows,bad_manifest))
    invalid_cases.append((rows,manifest(rows)[:-1]))
    for bad,bad_manifest in invalid_cases:
        step_before=ppo.optimizer_steps(optimizer)
        rejected={}
        try:
            ppo.ppo_update(model,optimizer,bad,torch.device('cpu'),rejected,episodes=bad_manifest)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid batch was accepted')
        assert rejected['optimizer_steps']==0 and ppo.optimizer_steps(optimizer)==step_before
    # Failure after an actual state advance, before step() returns, must still
    # report the real Adam step count rather than the completed callback count.
    fresh=load_checkpoint(V2/'checkpoints/threat-supply-initial-v3.pt')
    failed_optimizer=torch.optim.Adam(fresh.parameters(),lr=.0003)
    original_step=failed_optimizer.step
    calls=0
    def injected_step(*args,**kwargs):
        nonlocal calls
        result=original_step(*args,**kwargs)
        calls+=1
        if calls==3:
            raise RuntimeError('Synthetic failure after third applied Adam step')
        return result
    failed={}
    with patch.object(failed_optimizer,'step',injected_step):
        try:
            ppo.ppo_update(fresh,failed_optimizer,rows,torch.device('cpu'),failed,episodes=manifest(rows),epochs=2,minibatch_size=4)
        except RuntimeError as error:
            assert 'Synthetic failure' in str(error)
        else:
            raise AssertionError('Injected failure did not propagate')
    assert failed['optimizer_steps']==3 and failed['minibatches']==2 and not failed['completed']
    # An entirely forced rollout trains only critic; fresh Adam actor parameters
    # must remain exactly unchanged (no inherited momentum to move them).
    forced_only=[copy.deepcopy(row) for row in rows if row['episode_id']=='C']
    # Reuse the earlier optimizer with actual actor momentum. A forced-only
    # update must preserve all actor weights and optimizer states, not just
    # produce a mathematically zero direct policy gradient.
    actor_before={name:parameter.detach().clone() for name,parameter in model.named_parameters() if name.startswith('actor.')}
    actor_state_before={name:copy.deepcopy(optimizer.state[parameter])
                        for name,parameter in model.named_parameters() if name.startswith('actor.')}
    momentum_metrics=ppo.ppo_update(model,optimizer,forced_only,torch.device('cpu'),episodes=manifest(forced_only),epochs=1,minibatch_size=1)
    for name,parameter in model.named_parameters():
        if name.startswith('actor.'):
            assert torch.equal(parameter,actor_before[name])
            assert all(torch.equal(value,optimizer.state[parameter][key]) if isinstance(value,torch.Tensor)
                       else value==optimizer.state[parameter][key] for key,value in actor_state_before[name].items())
    assert momentum_metrics['group_optimizer_steps']==dict(actor=0,critic=2)
    fresh=load_checkpoint(V2/'checkpoints/threat-supply-initial-v3.pt')
    forced_metrics=ppo.ppo_update(fresh,torch.optim.Adam(fresh.parameters()),forced_only,torch.device('cpu'),
                                 episodes=manifest(forced_only),epochs=1,minibatch_size=2)
    assert forced_metrics['parameter_delta_from_previous_update']['actor']['changed_tensors']==0
    assert forced_metrics['parameter_delta_from_previous_update']['critic']['changed_tensors']>0
    assert not torch.cuda.is_initialized()
    snapshot=args.out/'sources';snapshot.mkdir()
    for path in (Path(__file__),Path(ppo.__file__)):
        shutil.copy2(path,snapshot/path.name)
    report=dict(passed=True,synthetic_only=True,game_started=False,GPU_initialized=False,
        protocol=ppo.PROTOCOL,original_objective=original,forced_extended_objective=extended_terms,
        repeated_episode_objective=repeated_terms,episode_objective_mass=objective_mass,
        actor_gradient_max_error_after_forced_duplication=actor_gradient_error,
        critic_gradient_max_error_after_episode_repetition=critic_gradient_error,
        successful_synthetic_update=successful,invalid_batches_rejected_without_step=len(invalid_cases),
        injected_failure=failed,all_forced_actor_unchanged=forced_metrics,
        inherited_momentum_all_forced_actor_and_state_unchanged=momentum_metrics,
        module_sha256=hashlib.sha256(Path(ppo.__file__).read_bytes()).hexdigest(),
        limitations='Synthetic CPU objective/gradient engineering only; no native training or ability evidence. '
                    'Invariance concerns global objectives/gradients, not identical stochastic optimizer trajectories after changing batch size.')
    (args.out/'AUDIT.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(passed=True,module_sha256=report['module_sha256'],actual_steps=successful['optimizer_steps'],
        actor_gradient_invariance_error=actor_gradient_error,critic_gradient_invariance_error=critic_gradient_error,
        failure_actual_steps=failed['optimizer_steps'],invalid_batches=len(invalid_cases)),indent=2))


if __name__=='__main__':
    main()
