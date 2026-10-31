"""Check an optional undiscounted finite-battle objective before experimenting."""
from pathlib import Path
import numpy as np
from lab_io import atomic_json
from masked_ppo import gae


rng = np.random.default_rng(2026101511)
checks = []
for gamma in [.99, 1.0]:
    for length in [2, 31, 100]:
        for winner in [-1., 1.]:
            potential = rng.uniform(-1, 1, length + 1)
            potential[-1] = 0.
            raw = np.zeros((length, 1), np.float32)
            raw[-1] = winner
            shaped = raw + .5 * (gamma * potential[1:] - potential[:-1])[:, None]
            discounted = float(np.sum(gamma ** np.arange(length) * shaped[:, 0]))
            expected = gamma ** (length - 1) * winner - .5 * potential[0]
            np.testing.assert_allclose(discounted, expected, atol=1e-6, rtol=0)
            terminated = np.zeros_like(raw, bool)
            terminated[-1] = True
            zeros = np.zeros_like(raw)
            advantages, returns = gae(shaped, zeros, zeros, terminated, np.zeros_like(terminated), gamma=gamma, lam=1.)
            np.testing.assert_allclose(returns[0, 0], expected, atol=2e-6, rtol=0)
            if gamma == 1.:
                np.testing.assert_allclose(discounted + .5 * potential[0], winner, atol=1e-6, rtol=0)
            checks.append(dict(gamma=gamma, length=length, terminal_reward=winner, passed=True))
# At a time cap, retain both real next-state bootstrap and next potential.
potential = np.asarray([.3, -.2, .4])
rewards = .5 * np.diff(potential)[:, None]
advantage, returns = gae(rewards, [[0.], [0.]], [[0.], [.7]],
                         [[False], [False]], [[False], [True]], gamma=1., lam=1.)
np.testing.assert_allclose(returns[0, 0], .5 * (.4 - .3) + .7, atol=1e-6)
atomic_json(Path(__file__).with_name('finite-win-objective-contract.json'), dict(
    passed=True, checks=checks, truncation_bootstrap_and_potential_passed=True,
    scope='Reward/GAE mathematics only; optional gamma1/step-cost0 has not been trained or shown stronger. Existing experiments retain gamma.99/step-cost.002 defaults.'))
print('Finite-battle win objective and shaping checks passed')
