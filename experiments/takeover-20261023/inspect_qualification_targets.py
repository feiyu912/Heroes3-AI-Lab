"""Read-only inspection of the frozen terminal-credit qualification targets."""
import hashlib
import json
from pathlib import Path

import torch

folder = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-native-20261023-01/qualification/phase-0')
target = torch.load(folder / 'TARGETS.pt', map_location='cpu', weights_only=False)
d = target['targets']
print('eligible', int(d['eligible'].sum()), 'of', len(d['eligible']))
print('first_suffix_end_step', d['first_suffix_end_step'])
print('reasons', d['reason'])
print('suffix_loss_rows', d['suffix_loss_rows'])
print('global_RNG_unchanged', target['global_RNG_unchanged'])
print('private_rng_equal', all(bool((a == b).all()) for a, b in zip(
    target['private_sampling_RNG_before'], target['private_sampling_RNG_after'])))
print('max_abs_delta', float(abs(d['candidate_advantage'] - d['base_advantage']).max()))
print('base_last_adv_first4', [round(float(x), 6) for x in d['base_advantage'][-1][:4]])
print('cand_last_adv_first4', [round(float(x), 6) for x in d['candidate_advantage'][-1][:4]])
print('targets_sha256', hashlib.sha256((folder / 'TARGETS.pt').read_bytes()).hexdigest())
print('workers', json.loads((folder / 'WORKERS.json').read_text())['torch_imported'])
