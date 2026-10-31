"""New-format prior residual model; all new visible-information weights migrate at zero."""
import hashlib
import io
import os
from pathlib import Path
import tempfile

import torch
from torch import nn
from encoder import STATE_DIM, CANDIDATE_DIM, ENCODER_VERSION

PRIOR_FORMAT = 'strategic-visible-threat-supply-prior-v3'


class PriorCandidateActorCritic(nn.Module):
    def __init__(self, hidden=64, prior_scale=64., prior_feature_index=13):
        super().__init__()
        if hidden < 1 or prior_scale <= 0 or not torch.isfinite(torch.tensor(prior_scale)) or prior_feature_index != 13:
            raise ValueError('Invalid visible strategic model configuration')
        self.hidden, self.prior_feature_index = hidden, prior_feature_index
        self.register_buffer('prior_scale', torch.tensor(float(prior_scale)))
        width = STATE_DIM + CANDIDATE_DIM
        def network():
            return nn.Sequential(nn.Linear(width, hidden), nn.Tanh(), nn.Linear(hidden, hidden), nn.Tanh(), nn.Linear(hidden, 1))
        self.actor, self.critic = network(), network()
        nn.init.zeros_(self.actor[-1].weight)
        nn.init.zeros_(self.actor[-1].bias)

    def forward(self, state, candidates, mask):
        if mask.dtype != torch.bool or mask.shape != candidates.shape[:2] or not bool(mask.any(dim=1).all()):
            raise ValueError('Invalid/nonempty legal mask required')
        if state.shape != (candidates.shape[0], STATE_DIM) or candidates.shape[-1] != CANDIDATE_DIM:
            raise ValueError('Wrong visible encoder dimensions')
        if not bool(torch.isfinite(state).all()) or not bool(torch.isfinite(candidates[mask]).all()):
            raise ValueError('Nonfinite legal visible features')
        clean = torch.where(mask[..., None], candidates, torch.zeros_like(candidates))
        joined = torch.cat((state[:, None, :].expand(-1, candidates.shape[1], -1), clean), dim=-1)
        logits = self.actor(joined).squeeze(-1) + self.prior_scale * clean[..., self.prior_feature_index]
        logits = logits.masked_fill(~mask, -torch.inf)
        pooled = clean.sum(dim=1) / mask.sum(dim=1, keepdim=True)
        value = self.critic(torch.cat((state, pooled), dim=-1)).squeeze(-1)
        return logits, value


def model_from_bundle(bundle, device='cpu'):
    if (bundle.get('format') != PRIOR_FORMAT or bundle.get('encoder_version') != ENCODER_VERSION or
            bundle.get('state_dim') != STATE_DIM or bundle.get('candidate_dim') != CANDIDATE_DIM):
        raise ValueError('Wrong threat/supply checkpoint format; use explicit migration for legacy weights')
    model = PriorCandidateActorCritic(bundle['hidden'], **bundle['prior_config']).to(device)
    model.load_state_dict(bundle['state_dict'], strict=True)
    if float(model.prior_scale) != bundle['prior_config']['prior_scale']:
        raise ValueError('Prior scale/state disagreement')
    if not all(bool(torch.isfinite(value).all()) for value in model.state_dict().values()):
        raise ValueError('Nonfinite model weight')
    return model.eval()


def load_checkpoint_bundle(path, device='cpu'):
    raw = Path(path).read_bytes()
    bundle = torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)
    return model_from_bundle(bundle, device), bundle, hashlib.sha256(raw).hexdigest()


def load_checkpoint(path, device='cpu'):
    return load_checkpoint_bundle(path, device)[0]


def atomic_torch_save(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            torch.save(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
