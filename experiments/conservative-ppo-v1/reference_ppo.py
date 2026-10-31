"""Masked PPO with optional detached KL(reference || learner) on legal actions."""
import importlib.util
from pathlib import Path
import numpy as np
import torch

_research = Path(__file__).resolve().parents[2]/'research'
_spec = importlib.util.spec_from_file_location('_reference_ppo_original', _research/'masked_ppo.py')
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
gae, distribution = _base.gae, _base.distribution


def legal_reference_kl(logits, mask, reference_log_probs):
    """Per-observation KL; never multiply padding zeros by negative infinity."""
    if mask.dtype != torch.bool or logits.shape != mask.shape:
        raise ValueError('Boolean legal mask must match logits')
    if len(reference_log_probs) != len(logits):
        raise ValueError('One reference legal distribution is required per observation')
    current = distribution(logits, mask).logits
    result = []
    for index, reference in enumerate(reference_log_probs):
        ref = torch.as_tensor(reference, dtype=logits.dtype, device=logits.device).detach()
        if ref.ndim != 1 or ref.numel() != int(mask[index].sum()):
            raise ValueError('Reference legal distribution length differs from mask')
        if not bool(torch.isfinite(ref).all()):
            raise ValueError('Nonfinite reference legal log probability')
        if abs(float(torch.logsumexp(ref,0))) > 1e-4:
            raise ValueError('Reference values must be normalized legal log probabilities')
        legal_current = current[index][mask[index]]
        result.append((ref.exp() * (ref-legal_current)).sum())
    return torch.stack(result)


def encode_reference(reference_pair, raw_observations, collate_fn, batch_size=24):
    """Encode raw observations using reference's own body; return CPU legal rows."""
    if batch_size < 1 or not raw_observations:
        raise ValueError('Need observations and positive batch size')
    parameters = tuple(reference_pair.parameters())
    if not parameters or any(parameter.requires_grad for parameter in parameters):
        raise ValueError('Reference parameters must be frozen before encoding')
    if reference_pair.training:
        raise ValueError('Reference must be in eval mode')
    versions = [parameter._version for parameter in parameters]
    device = parameters[0].device
    log_probs, action_ids = [], []
    with torch.inference_mode():
        for start in range(0,len(raw_observations),batch_size):
            observations = raw_observations[start:start+batch_size]
            # Deliberately re-encode the raw observations with this reference.
            features = reference_pair.encode_features(observations)
            batch = collate_fn(features,device)
            logits, _ = reference_pair(*batch)
            mask = batch[-1]
            logp = distribution(logits,mask).logits
            for index,observation in enumerate(observations):
                ids = [int(value) for value in observation['active_action_ids']]
                if len(ids) != int(mask[index].sum()) or len(ids) != len(set(ids)):
                    raise ValueError('Reference encoding changed the legal candidates')
                log_probs.append(logp[index][mask[index]].cpu().clone())
                action_ids.append(ids)
    if versions != [parameter._version for parameter in parameters]:
        raise AssertionError('Reference changed while encoding')
    return dict(log_probs=log_probs,action_ids=action_ids,encoding_batch_size=batch_size,
                provenance='Frozen reference independently encoded these raw observations')


def update(model, optimizer, inputs, actions, old_logp, old_values, advantages, returns,
           epochs=3, batch_size=64, clip=0.2, entropy_coef=0.01, target_kl=0.03,
           recompute_atol=2e-4, recompute_rtol=0., recompute_batch_size=None,
           reference_log_probs=None, reference_action_ids=None, candidate_action_ids=None,
           reference_coef=0., collate_fn=None, reference_parameters=()):
    """Same PPO objective plus coef*mean legal reference KL; reference is never fit."""
    if reference_coef < 0 or not np.isfinite(reference_coef):
        raise ValueError('Reference coefficient must be finite and nonnegative')
    if recompute_atol > 2e-4 or recompute_rtol != 0:
        raise ValueError('Recompute gate must retain atol <= 2e-4 and rtol == 0')
    if not inputs or epochs < 1 or batch_size < 1:
        raise ValueError('Need samples, epochs, and a positive batch size')
    if recompute_batch_size is None or recompute_batch_size < 1:
        raise ValueError('Pass the original rollout inference batch size explicitly')
    if collate_fn is None:
        from decision_model import collate as collate_fn
    reference_parameters = tuple(reference_parameters)
    optimizer_ids = {id(parameter) for group in optimizer.param_groups for parameter in group['params']}
    learner_ids = {id(parameter) for parameter in model.parameters()}
    if any(parameter.requires_grad for parameter in reference_parameters):
        raise ValueError('Reference parameters must be frozen')
    if any(id(parameter) in optimizer_ids or id(parameter) in learner_ids for parameter in reference_parameters):
        raise ValueError('Reference parameters must be disjoint from learner and optimizer')
    if reference_coef:
        if reference_log_probs is None or reference_action_ids is None or candidate_action_ids is None:
            raise ValueError('Reference KL requires distributions and both ordered action ID lists')
        if not (len(reference_log_probs) == len(reference_action_ids) == len(candidate_action_ids) == len(inputs)):
            raise ValueError('Reference sample count mismatch')
        for reference_ids,candidate_ids,reference_row in zip(reference_action_ids,candidate_action_ids,reference_log_probs):
            ref, current = list(map(int,reference_ids)), list(map(int,candidate_ids))
            if ref != current or not ref or len(ref) != len(set(ref)) or len(ref) != len(reference_row):
                raise ValueError('Reference candidate identities/order differ from learner')
    device = next(model.parameters()).device
    actions = torch.as_tensor(actions,dtype=torch.long,device=device)
    old_logp,old_values,advantages,returns = (torch.as_tensor(value,dtype=torch.float32,device=device)
        for value in [old_logp,old_values,advantages,returns])
    advantages = (advantages-advantages.mean())/advantages.std(unbiased=False).clamp(min=1e-8)
    assert all(torch.isfinite(value).all() for value in [old_logp,old_values,advantages,returns])
    maximum_recompute_error = 0.
    with torch.inference_mode():
        for start in range(0,len(inputs),recompute_batch_size):
            batch = collate_fn(inputs[start:start+recompute_batch_size],device)
            logits,_ = model(*batch)
            current = distribution(logits,batch[-1]).log_prob(actions[start:start+recompute_batch_size])
            maximum_recompute_error = max(maximum_recompute_error,float((current-old_logp[start:start+recompute_batch_size]).abs().max()))
            torch.testing.assert_close(current,old_logp[start:start+recompute_batch_size],atol=recompute_atol,rtol=0.)
            if reference_coef:
                legal_reference_kl(logits,batch[-1],reference_log_probs[start:start+recompute_batch_size])
    metrics = []
    for epoch in range(epochs):
        epoch_kl = []
        for indices in torch.randperm(len(inputs)).split(batch_size):
            batch = collate_fn([inputs[index] for index in indices.tolist()],device)
            logits,values = model(*batch)
            dist = distribution(logits,batch[-1])
            logp = dist.log_prob(actions[indices])
            log_ratio = logp-old_logp[indices]
            ratio = log_ratio.exp()
            policy_loss = -torch.minimum(ratio*advantages[indices],ratio.clamp(1-clip,1+clip)*advantages[indices]).mean()
            value_loss = ((values-returns[indices])**2).mean()
            entropy = dist.entropy().mean()
            loss = policy_loss+0.5*value_loss-entropy_coef*entropy
            reference_kl = logits.new_zeros(())
            if reference_coef:
                reference_rows = [reference_log_probs[index] for index in indices.tolist()]
                reference_kl = legal_reference_kl(logits,batch[-1],reference_rows).mean()
                loss = loss+reference_coef*reference_kl
            assert torch.isfinite(loss)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(),0.5)
            assert torch.isfinite(norm)
            optimizer.step()
            with torch.no_grad():
                kl = ((ratio-1)-log_ratio).mean().item()
                epoch_kl.append(kl)
                metrics.append(dict(loss=loss.item(),policy_loss=policy_loss.item(),value_loss=value_loss.item(),
                    entropy=entropy.item(),approximate_kl=kl,gradient_norm=norm.item(),
                    clip_fraction=((ratio-1).abs()>clip).float().mean().item(),reference_kl=reference_kl.item()))
        if np.mean(epoch_kl) > target_kl:
            break
    return {key:float(np.mean([row[key] for row in metrics])) for key in metrics[0]} | dict(
        epochs_completed=epoch+1,maximum_recompute_logp_error=maximum_recompute_error,
        recompute_batch_size=recompute_batch_size,reference_coef=float(reference_coef))
