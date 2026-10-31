"""Explicit episode-balanced choice PPO. Independent of frozen transition-uniform v1.

Collector must certify complete native episodes before calling ppo_update.
The module rejects invalid/missing terminal samples before any optimizer step.
"""
from collections import Counter, defaultdict
import importlib.util
import math
from pathlib import Path
import sys

import torch
from torch.distributions import Categorical

TYPED = Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('_typed_ppo_encoder',TYPED/'encoder.py')
encoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(encoder)
collate,validate=encoder.collate,encoder.validate

PROTOCOL = dict(schema='strategic-learned-build-episode-balanced-choice-ppo-v1', action_schema='strategy-candidates-v5', gamma=1.0,
    reward='Completed native terminal win +1/loss -1 only; invalid batch must abort before update.',
    actor_sample_weight='N/(E*episode_free_choices) if candidate_count>1, otherwise 0; E includes zero-choice episodes',
    critic_sample_weight='N/(E*episode_steps); E includes all valid episodes',
    advantage='return-old_value; weighted mean/variance only over free choices, equal mass per active episode',
    entropy='Same weights as actor, zero for forced transitions',
    KL='Report objective-weighted and conditional free-choice KL; gate conditional KL to avoid zero-choice dilution',
    minibatches='Uniform random transitions; global N/E weights retained, not renormalized within minibatch',
    forced_actor_optimizer='If current minibatch has no free choices, set actor gradients to None; skip actor momentum/decay/state advance',
    epochs=4, minibatch_size=64, clip=.2, value_coefficient=.5, entropy_coefficient=.005,
    max_gradient_norm=.5, max_conditional_KL=.05,
    limitations='Move/EndTurn/once-per-turn real BuildStructure policy; automatic EndTurn/recruit/transfers excluded; native battles delegated. No ability improvement implied.')


def optimizer_steps(optimizer):
    return max((int(state['step']) for state in optimizer.state.values() if 'step' in state), default=0)


def group_optimizer_steps(model,optimizer,group):
    return max((int(optimizer.state.get(parameter,{}).get('step',0))
                for name,parameter in model.named_parameters() if name.startswith(group+'.')),default=0)


def parameter_snapshot(model):
    return {name: parameter.detach().cpu().clone() for name, parameter in model.named_parameters()}


def parameter_delta(model, before):
    result = {}
    for group in ('actor', 'critic'):
        deltas = [(parameter.detach().cpu().double()-before[name].double())
                  for name, parameter in model.named_parameters() if name.startswith(group+'.')]
        result[group] = dict(changed_tensors=sum(bool(delta.ne(0).any()) for delta in deltas),
            total_tensors=len(deltas), l2_delta=sum(float(delta.square().sum()) for delta in deltas)**.5,
            max_abs_delta=max((float(delta.abs().max()) for delta in deltas), default=0.))
    return result


def prepare_batch(samples, device='cpu', *, episodes=None):
    """Validate first; return immutable global weights and advantage moments.

    Optional episodes is the collector's complete manifest. Production callers
    must pass it to establish that no invalid or zero-row episode was omitted.
    """
    if not samples:
        raise ValueError('Empty sample batch; no update allowed')
    lengths, choices, rewards = Counter(), Counter(), {}
    for sample in samples:
        identity = sample.get('episode_id')
        if not isinstance(identity, (str, int)) or isinstance(identity, bool) or identity == '':
            raise ValueError('Stable explicit episode_id required')
        if sample.get('valid') is False:
            raise ValueError('Invalid episode transition; abort entire batch')
        reward = sample.get('return')
        if isinstance(reward, bool) or reward not in (-1., 1.):
            raise ValueError('Only completed native +/-1 returns accepted; null timeout is not a loss')
        if identity in rewards and rewards[identity] != reward:
            raise ValueError('Terminal returns disagree within one episode')
        rewards[identity] = reward
        request = validate(sample['request'])
        if (sample.get('execution_verified') is not True or type(sample.get('native_request_id')) is not int or sample['native_request_id']<1
                or sample.get('decision_id')!=request['request_id'] or not isinstance(sample.get('policy_sha256'),str) or len(sample['policy_sha256'])!=64):
            raise ValueError('Typed sample requires certified real native binding and policy provenance')
        action = sample.get('action')
        if type(action) is not int or not 0 <= action < len(request['candidates']):
            raise ValueError('Illegal archived action')
        if sample.get('action_type')!=request['candidates'][action]['op']:
            raise ValueError('Typed sample action operation differs from selected candidate')
        for field in ('old_logprob', 'old_value'):
            value = sample.get(field)
            if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
                raise ValueError('Invalid archived '+field)
        if sample['old_logprob'] > 1e-5:
            raise ValueError('Archived log probability must not be positive')
        free = len(request['candidates']) > 1
        if not free and abs(sample['old_logprob']) > 1e-5:
            raise ValueError('Forced transition must have log probability zero')
        lengths[identity] += 1
        choices[identity] += free
    if episodes is not None:
        manifest = {}
        for episode in episodes:
            identity = episode.get('episode_id')
            if identity in manifest or identity not in lengths:
                raise ValueError('Duplicate/missing/zero-transition episode in manifest')
            if (episode.get('valid') is not True or episode.get('reward') != rewards[identity] or
                    not episode.get('native_consumption_verified', False) or
                    not episode.get('native',{}).get('completed') or not episode.get('native',{}).get('inputs_unchanged')):
                raise ValueError('Collector did not certify a valid complete native episode')
            if episode.get('sampling_replay_exact') is not True or any(s['policy_sha256']!=episode.get('checkpoint_sha256') for s in samples if s['episode_id']==identity):
                raise ValueError('Exact on-policy replay and checkpoint binding required')
            if episode.get('decisions', lengths[identity]) != lengths[identity]:
                raise ValueError('Manifest/sample decision count mismatch')
            manifest[identity] = episode
        if manifest.keys() != lengths.keys():
            raise ValueError('Sample episodes differ from certified collector manifest')
    size, total_episodes = len(samples), len(lengths)
    actor_weights = torch.tensor([size/(total_episodes*choices[sample['episode_id']])
        if len(sample['request']['candidates'])>1 else 0. for sample in samples], dtype=torch.float32, device=device)
    critic_weights = torch.tensor([size/(total_episodes*lengths[sample['episode_id']]) for sample in samples],
                                  dtype=torch.float32, device=device)
    returns = torch.tensor([sample['return'] for sample in samples], dtype=torch.float32, device=device)
    advantages = returns-torch.tensor([sample['old_value'] for sample in samples], dtype=torch.float32, device=device)
    weight_sum = actor_weights.sum()
    if float(weight_sum)>0:
        # Moments do not depend on total N. Compute in double precision to avoid
        # changing normalization merely by adding zero-weight forced rows.
        moments = torch.tensor([1./choices[sample['episode_id']] if len(sample['request']['candidates'])>1 else 0.
                                for sample in samples],dtype=torch.float64,device=device)
        raw = advantages.double()
        mean = (moments*raw).sum()/moments.sum()
        variance = (moments*(raw-mean).square()).sum()/moments.sum()
        normalized = torch.where(actor_weights>0,((raw-mean)/variance.sqrt().clamp_min(1e-6)).float(),0.)
    else:
        mean, variance = torch.zeros((),device=device), torch.zeros((),device=device)
        normalized = torch.zeros_like(advantages)
    return dict(actor_weights=actor_weights, critic_weights=critic_weights, advantages=normalized, returns=returns,
        old_logprob=torch.tensor([sample['old_logprob'] for sample in samples],dtype=torch.float32,device=device),
        metadata=dict(samples=size, episodes=total_episodes, free_choices=sum(choices.values()),
            forced_transitions=size-sum(choices.values()), active_actor_episodes=sum(count>0 for count in choices.values()),
            actor_weight_sum=float(weight_sum), critic_weight_sum=float(critic_weights.sum()),
            advantage_mean=float(mean), advantage_variance=float(variance),
            per_episode=[dict(episode_id=identity,steps=lengths[identity],free_choices=choices[identity],reward=rewards[identity])
                         for identity in lengths], collector_manifest_verified=episodes is not None))


def objective_terms(model, samples, prepared, device='cpu', indices=None):
    """Global weight factors stay fixed even for a small/forced-only minibatch."""
    indices = list(range(len(samples))) if indices is None else list(indices)
    if not indices:
        raise ValueError('Empty objective minibatch')
    select = torch.tensor(indices, device=device)
    logits, values = model(**collate([samples[index]['request'] for index in indices],device))
    distribution = Categorical(logits=logits)
    actions = torch.tensor([samples[index]['action'] for index in indices], device=device)
    logprob = distribution.log_prob(actions)
    difference = logprob-prepared['old_logprob'][select]
    ratio = difference.exp()
    if not bool(torch.isfinite(ratio).all()):
        raise ValueError('Nonfinite importance ratio; update aborted')
    actor_weight, critic_weight = prepared['actor_weights'][select],prepared['critic_weights'][select]
    advantage = prepared['advantages'][select]
    actor = -(actor_weight*torch.minimum(ratio*advantage,ratio.clamp(.8,1.2)*advantage)).mean()
    critic = .5*(critic_weight*(values-prepared['returns'][select]).square()).mean()
    entropy = (actor_weight*distribution.entropy()).mean()
    kl = (actor_weight*((ratio-1)-difference)).mean()
    active_mass = prepared['metadata']['active_actor_episodes']/prepared['metadata']['episodes']
    conditional_kl = kl/active_mass if active_mass>0 else kl*0
    return dict(actor=actor,critic=critic,entropy=entropy,kl=kl,conditional_kl=conditional_kl,
                loss=actor+.5*critic-.005*entropy)


def ppo_update(model, optimizer, samples, device, progress=None, *, episodes=None, epochs=4, minibatch_size=64):
    if not isinstance(optimizer,(torch.optim.Adam,torch.optim.AdamW)):
        raise ValueError('Auditable Adam/AdamW optimizer state required')
    if epochs<1 or minibatch_size<1:
        raise ValueError('Positive epochs/minibatch_size required')
    progress = progress if progress is not None else {}
    initial_steps = optimizer_steps(optimizer)
    initial_group_steps = {group:group_optimizer_steps(model,optimizer,group) for group in ('actor','critic')}
    before = parameter_snapshot(model)
    progress.update(optimizer_steps=0, minibatches=0, completed=False, early_stop_kl=False,
                    forced_only_minibatches=0,
                    algorithm_schema=PROTOCOL['schema'])
    try:
        if episodes is None:
            raise ValueError('Complete certified collector episode manifest required before optimizer update')
        prepared = prepare_batch(samples,device,episodes=episodes)
        progress['weighting'] = prepared['metadata']
        for epoch in range(epochs):
            for indices in torch.randperm(len(samples)).split(minibatch_size):
                terms = objective_terms(model,samples,prepared,device,indices.tolist())
                if not all(bool(torch.isfinite(value)) for value in terms.values()):
                    raise ValueError('Nonfinite objective; update aborted')
                # All rows share uniform minibatch sampling; weights use full N/E.
                optimizer.zero_grad(set_to_none=True)
                terms['loss'].backward()
                if not any(len(samples[index]['request']['candidates'])>1 for index in indices.tolist()):
                    # Zero tensors still let Adam momentum or AdamW decay move
                    # an actor. None makes both optimizers skip the parameter,
                    # preserving its weights, moments and per-parameter step.
                    for name,parameter in model.named_parameters():
                        if name.startswith('actor.'):
                            parameter.grad=None
                    progress['forced_only_minibatches']+=1
                if not all(parameter.grad is None or bool(torch.isfinite(parameter.grad).all()) for parameter in model.parameters()):
                    raise ValueError('Nonfinite gradient; update aborted')
                torch.nn.utils.clip_grad_norm_(model.parameters(),.5)
                try:
                    optimizer.step()
                finally:
                    progress['optimizer_steps'] = optimizer_steps(optimizer)-initial_steps
                progress['minibatches'] += 1
                progress['last'] = {name:float(value.detach()) for name,value in terms.items()}
            # Evaluate the complete weighted sample objective after each epoch;
            # a forced-only minibatch must not hide KL on the free choices.
            with torch.no_grad():
                total = {name:0. for name in ('actor','critic','entropy','kl','conditional_kl','loss')}
                for offset in range(0,len(samples),minibatch_size):
                    batch = list(range(offset,min(offset+minibatch_size,len(samples))))
                    terms = objective_terms(model,samples,prepared,device,batch)
                    for name,value in terms.items():
                        total[name] += float(value)*len(batch)/len(samples)
            progress['epoch'] = epoch+1
            progress['full_batch_post_epoch'] = total
            if total['conditional_kl']>.05:
                progress['early_stop_kl']=True
                break
        progress['completed']=True
        return progress
    except BaseException as error:
        progress['error']=repr(error)
        raise
    finally:
        progress['optimizer_steps']=optimizer_steps(optimizer)-initial_steps
        progress['group_optimizer_steps']={group:group_optimizer_steps(model,optimizer,group)-initial_group_steps[group]
                                           for group in ('actor','critic')}
        progress['parameter_delta_from_previous_update']=parameter_delta(model,before)

