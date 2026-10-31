import json
from pathlib import Path
import numpy as np
import torch
from decision_model import DecisionModel, collate, load_dataset
from masked_ppo import gae, distribution

torch.set_num_threads(1)
samples = load_dataset('/root/heroes3-ai-lab/datasets/teacher-v2', 'validation')
small = min(samples, key=lambda s: len(s['features'][1]))['features']
large = max(samples, key=lambda s: len(s['features'][1]))['features']
checks = []
for architecture in ['mlp', 'attention', 'gnn']:
    model = DecisionModel(architecture).eval()
    with torch.inference_mode():
        alone = collate([small])
        mixed = collate([small, large])
        la, va = model(*alone)
        lm, vm = model(*mixed)
        torch.testing.assert_close(la[0], lm[0, :la.shape[1]], atol=2e-6, rtol=1e-5)
        torch.testing.assert_close(va[0], vm[0], atol=2e-6, rtol=1e-5)
        dist = distribution(lm, mixed[-1])
        assert (dist.probs[~mixed[-1]] == 0).all()
        assert torch.allclose(dist.probs.sum(-1), torch.ones(2))
        for _ in range(100):
            actions = dist.sample()
            assert mixed[-1][torch.arange(2), actions].all()
        permutation = np.arange(len(small[1]))[::-1].copy()
        permuted = (small[0], small[1][permutation], small[2], small[3][permutation])
        lp, _ = model(*collate([permuted]))
        torch.testing.assert_close(lp[0], la[0, permutation])
    checks.append(architecture + ': padding, legal-only probabilities, sampling, candidate permutation')

# Terminal return must ignore next-episode values. Truncation bootstraps its final state
# and must not propagate the next episode's advantage.
adv, ret = gae([[1], [2]], [[0.5], [0.7]], [[100], [3]], [[True], [False]], [[False], [True]], gamma=0.9, lam=1)
np.testing.assert_allclose(ret[:, 0], [1, 4.7], atol=1e-6)
checks.append('GAE: termination removes bootstrap; truncation uses final value and stops trace')
adv, ret = gae([[0], [1]], [[0], [0]], [[0], [0]], [[False], [True]], [[False], [False]], gamma=1, lam=1)
np.testing.assert_allclose(ret[:, 0], [1, 1])
checks.append('GAE: complete episode reward propagates backward')
try:
    distribution(torch.zeros(1, 2), torch.zeros(1, 2, dtype=torch.bool))
except ValueError:
    checks.append('Empty legal set rejected')
else:
    raise AssertionError('Empty mask accepted')
Path('/mnt/g/Heroes3-AI-Lab/research/training-contract-tests.json').write_text(json.dumps(dict(passed=True, checks=checks), indent=2))
print('PASSED', len(checks), 'training contracts')
