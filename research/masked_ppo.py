"""Masked PPO math with separate bootstrap and episode-continuation masks."""
import numpy as np
import torch


def gae(rewards, values, next_values, terminated, truncated, gamma=0.99, lam=0.95):
    rewards, values, next_values = (np.asarray(v, np.float32) for v in [rewards, values, next_values])
    terminated, truncated = np.asarray(terminated, bool), np.asarray(truncated, bool)
    assert rewards.shape == values.shape == next_values.shape == terminated.shape == truncated.shape
    advantages = np.zeros_like(rewards)
    tail = np.zeros(rewards.shape[1:], np.float32)
    for t in range(len(rewards) - 1, -1, -1):
        delta = rewards[t] + gamma * next_values[t] * (~terminated[t]) - values[t]
        tail = delta + gamma * lam * (~(terminated[t] | truncated[t])) * tail
        advantages[t] = tail
    return advantages, advantages + values


def distribution(logits, mask):
    if not bool(mask.any(-1).all()):
        raise ValueError('No legal action')
    if not bool(torch.isfinite(logits[mask]).all()):
        raise ValueError('Nonfinite legal logit')
    return torch.distributions.Categorical(logits=logits.masked_fill(~mask, -torch.inf))


def update(model, optimizer, inputs, actions, old_logp, old_values, advantages, returns,
           epochs=3, batch_size=64, clip=0.2, entropy_coef=0.01, target_kl=0.03,
           recompute_atol=2e-5, recompute_rtol=2e-5, recompute_batch_size=None):
    from decision_model import collate
    device = next(model.parameters()).device
    actions = torch.as_tensor(actions, dtype=torch.long, device=device)
    old_logp, old_values, advantages, returns = (torch.as_tensor(v, dtype=torch.float32, device=device)
                                               for v in [old_logp, old_values, advantages, returns])
    advantages = (advantages - advantages.mean()) / advantages.std(unbiased=False).clamp(min=1e-8)
    assert all(torch.isfinite(v).all() for v in [old_logp, old_values, advantages, returns])
    metrics = []
    # Recompute once before any update using exactly the stored candidates/masks.
    maximum_recompute_error=0.
    check_batch_size=recompute_batch_size or batch_size
    with torch.inference_mode():
        for start in range(0, len(inputs), check_batch_size):
            batch = collate(inputs[start:start + check_batch_size], device)
            logits, _ = model(*batch)
            current = distribution(logits, batch[-1]).log_prob(actions[start:start + check_batch_size])
            maximum_recompute_error=max(maximum_recompute_error,float((current-old_logp[start:start+check_batch_size]).abs().max()))
            torch.testing.assert_close(current, old_logp[start:start + check_batch_size], atol=recompute_atol, rtol=recompute_rtol)
    for epoch in range(epochs):
        epoch_kl = []
        for indices in torch.randperm(len(inputs)).split(batch_size):
            batch = collate([inputs[i] for i in indices.tolist()], device)
            logits, values = model(*batch)
            dist = distribution(logits, batch[-1])
            logp = dist.log_prob(actions[indices])
            log_ratio = logp - old_logp[indices]
            ratio = log_ratio.exp()
            policy_loss = -torch.minimum(ratio * advantages[indices],
                                          ratio.clamp(1-clip, 1+clip) * advantages[indices]).mean()
            value_loss = ((values - returns[indices]) ** 2).mean()
            entropy = dist.entropy().mean()
            loss = policy_loss + 0.5 * value_loss - entropy_coef * entropy
            assert torch.isfinite(loss)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 0.5)
            assert torch.isfinite(norm)
            optimizer.step()
            with torch.no_grad():
                kl = ((ratio - 1) - log_ratio).mean().item()
                epoch_kl.append(kl)
                metrics.append(dict(loss=loss.item(), policy_loss=policy_loss.item(),
                                    value_loss=value_loss.item(), entropy=entropy.item(),
                                    approximate_kl=kl, gradient_norm=norm.item(),
                                    clip_fraction=((ratio - 1).abs() > clip).float().mean().item()))
        if np.mean(epoch_kl) > target_kl:
            break
    return {key: float(np.mean([m[key] for m in metrics])) for key in metrics[0]} | {'epochs_completed': epoch+1,'maximum_recompute_logp_error':maximum_recompute_error,'recompute_batch_size':check_batch_size}
