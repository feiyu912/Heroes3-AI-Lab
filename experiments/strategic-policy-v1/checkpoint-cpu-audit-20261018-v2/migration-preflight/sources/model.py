"""Small independent strategic actor-critic. Value is an uncalibrated scalar."""
import torch
from torch import nn
from encoder import CANDIDATE_DIM, STATE_DIM, ENCODER_VERSION

FORMAT = 'strategic-candidate-actor-critic-v1'
PRIOR_FORMAT = 'strategic-candidate-prior-residual-v2'


class CandidateActorCritic(nn.Module):
    def __init__(self, hidden=64):
        super().__init__()
        self.hidden = hidden
        width = STATE_DIM + CANDIDATE_DIM
        self.actor = nn.Sequential(nn.Linear(width, hidden), nn.Tanh(),
                                   nn.Linear(hidden, hidden), nn.Tanh(), nn.Linear(hidden, 1))
        self.critic = nn.Sequential(nn.Linear(width, hidden), nn.Tanh(),
                                    nn.Linear(hidden, hidden), nn.Tanh(), nn.Linear(hidden, 1))

    def forward(self, state, candidates, mask):
        if mask.dtype != torch.bool or mask.shape != candidates.shape[:2]:
            raise ValueError('Invalid candidate mask')
        if not torch.all(mask.any(dim=1)):
            raise ValueError('Each observation must have at least one legal candidate')
        clean = torch.where(mask[..., None], candidates, torch.zeros_like(candidates))
        expanded_state = state[:, None, :].expand(-1, candidates.shape[1], -1)
        logits = self.actor(torch.cat((expanded_state, clean), dim=-1)).squeeze(-1)
        logits = logits.masked_fill(~mask, -torch.inf)
        pooled = clean.sum(dim=1) / mask.sum(dim=1, keepdim=True)
        value = self.critic(torch.cat((state, pooled), dim=-1)).squeeze(-1)
        return logits, value


class PriorCandidateActorCritic(CandidateActorCritic):
    """A fixed positive heuristic prior plus a trainable, initially-zero residual."""
    def __init__(self, hidden=64, prior_scale=64.0, prior_feature_index=13):
        if prior_scale <= 0 or not torch.isfinite(torch.tensor(prior_scale)):
            raise ValueError('prior_scale must be finite and positive')
        if prior_feature_index != 13:
            raise ValueError('This encoder version stores heuristic tanh at feature 13')
        super().__init__(hidden)
        self.register_buffer('prior_scale', torch.tensor(float(prior_scale)))
        self.prior_feature_index = prior_feature_index
        nn.init.zeros_(self.actor[-1].weight)
        nn.init.zeros_(self.actor[-1].bias)

    def forward(self, state, candidates, mask):
        residual_logits, value = super().forward(state, candidates, mask)
        prior = torch.where(mask, candidates[..., self.prior_feature_index],
                            torch.zeros_like(candidates[..., self.prior_feature_index]))
        return residual_logits + self.prior_scale * prior, value


def load_checkpoint(path, device='cpu'):
    bundle = torch.load(path, map_location=device, weights_only=True)
    if bundle.get('format') not in (FORMAT, PRIOR_FORMAT) or bundle.get('encoder_version') != ENCODER_VERSION:
        raise ValueError('Wrong strategic model/encoder format')
    if bundle['format'] == PRIOR_FORMAT:
        model = PriorCandidateActorCritic(bundle['hidden'], **bundle['prior_config']).to(device)
    else:
        model = CandidateActorCritic(bundle['hidden']).to(device)
    model.load_state_dict(bundle['state_dict'], strict=True)
    if bundle['format'] == PRIOR_FORMAT and float(model.prior_scale) != bundle['prior_config']['prior_scale']:
        raise ValueError('Prior config/state mismatch')
    model.eval()
    return model
