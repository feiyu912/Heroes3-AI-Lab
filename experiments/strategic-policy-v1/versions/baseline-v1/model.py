"""Small independent strategic actor-critic. Value is an uncalibrated scalar."""
import torch
from torch import nn
from encoder import CANDIDATE_DIM, STATE_DIM, ENCODER_VERSION

FORMAT = 'strategic-candidate-actor-critic-v1'


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


def load_checkpoint(path, device='cpu'):
    bundle = torch.load(path, map_location=device, weights_only=True)
    if bundle.get('format') != FORMAT or bundle.get('encoder_version') != ENCODER_VERSION:
        raise ValueError('Wrong strategic model/encoder format')
    model = CandidateActorCritic(bundle['hidden']).to(device)
    model.load_state_dict(bundle['state_dict'], strict=True)
    model.eval()
    return model
