"""CPU typed-action prototype. This format supports weights loading, not training resume."""
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile

import torch
from torch import nn

_spec = importlib.util.spec_from_file_location('_typed_schema4_encoder', Path(__file__).with_name('encoder.py'))
encoder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(encoder)
STATE_DIM, CANDIDATE_DIM = encoder.STATE_DIM, encoder.CANDIDATE_DIM
ENCODER_VERSION = encoder.ENCODER_VERSION
PRIOR_FORMAT = 'strategic-typed-single-hero-prior-v4'
FORBIDDEN_RESUME_KEYS = {'optimizer', 'optimizer_state_dict', 'rollout', 'rows', 'collection_boundary',
                         'episode_generator_states', 'rng', 'cuda_rng', 'python_rng'}
WEIGHTS_KEYS = {'format', 'schema', 'encoder_version', 'state_dim', 'candidate_dim', 'hidden',
                'prior_config', 'state_dict', 'resume_supported', 'checkpoint_kind',
                'schema4_optimizer_steps', 'lineage'}


class PriorCandidateActorCritic(nn.Module):
    def __init__(self, hidden=64, prior_scale=64., prior_feature_index=13, stop_bias=-4.):
        super().__init__()
        if type(hidden) is not int or hidden < 1 or prior_feature_index != 13:
            raise ValueError('Invalid typed model configuration')
        if not all(torch.isfinite(torch.tensor(float(x))) for x in (prior_scale, stop_bias)) or prior_scale <= 0:
            raise ValueError('Invalid model prior')
        self.hidden, self.prior_feature_index = hidden, prior_feature_index
        self.register_buffer('prior_scale', torch.tensor(float(prior_scale)))
        def network():
            return nn.Sequential(nn.Linear(STATE_DIM + CANDIDATE_DIM, hidden), nn.Tanh(),
                                 nn.Linear(hidden, hidden), nn.Tanh(), nn.Linear(hidden, 1))
        self.actor, self.critic = network(), network()
        self.actor.register_parameter('stop_bias', nn.Parameter(torch.tensor(float(stop_bias))))
        nn.init.zeros_(self.actor[-1].weight)
        nn.init.zeros_(self.actor[-1].bias)

    def forward(self, state, candidates, mask):
        if candidates.ndim != 3 or candidates.shape[0] < 1 or mask.dtype != torch.bool or mask.shape != candidates.shape[:2]:
            raise ValueError('Invalid mask or feature rank')
        if not bool(mask.any(dim=1).all()):
            raise ValueError('All-masked legal action row')
        if state.shape != (candidates.shape[0], STATE_DIM) or candidates.shape[-1] != CANDIDATE_DIM:
            raise ValueError('Wrong typed encoder dimensions')
        if not bool(torch.isfinite(state).all()) or not bool(torch.isfinite(candidates[mask]).all()):
            raise ValueError('Nonfinite legal feature')
        clean = torch.where(mask[..., None], candidates, torch.zeros_like(candidates))
        bits = clean[..., -2:][mask]
        if not bool(((bits == 0.) | (bits == 1.)).all()) or not bool((bits.sum(-1) == 1.).all()):
            raise ValueError('Legal op bits must be one-hot')
        stop = mask & (clean[..., -1] == 1.)
        if bool((clean[..., :23][stop] != 0.).any()) or not bool((state[:, -1] == 1.).all()):
            raise ValueError('Nonzero stop move payload or unsupported hero count')
        joined = torch.cat((state[:, None, :].expand(-1, candidates.shape[1], -1), clean), dim=-1)
        logits = (self.actor(joined).squeeze(-1) + self.prior_scale * clean[..., 13] * clean[..., -2]
                  + self.actor.stop_bias * clean[..., -1])
        logits = logits.masked_fill(~mask, -torch.inf)
        pooled = clean.sum(dim=1) / mask.sum(dim=1, keepdim=True)
        value = self.critic(torch.cat((state, pooled), dim=-1)).squeeze(-1)
        return logits, value


def model_from_bundle(bundle, device='cpu'):
    if (not isinstance(bundle, dict) or set(bundle) != WEIGHTS_KEYS
            or bundle.get('format') != PRIOR_FORMAT or bundle.get('encoder_version') != ENCODER_VERSION
            or bundle.get('state_dim') != STATE_DIM or bundle.get('candidate_dim') != CANDIDATE_DIM
            or bundle.get('schema') != encoder.SCHEMA or bundle.get('resume_supported') is not False
            or FORBIDDEN_RESUME_KEYS.intersection(bundle)):
        raise ValueError('Typed weights-only format required; optimizer/rollout resume unsupported')
    if (bundle['checkpoint_kind'] != 'weights_only_initialization' or type(bundle['schema4_optimizer_steps']) is not int
            or bundle['schema4_optimizer_steps'] != 0 or not isinstance(bundle['lineage'], dict)
            or not all(bundle['lineage'].get(key) is True for key in ('reset_optimizer', 'reset_rng', 'discard_rollout', 'weights_only'))):
        raise ValueError('Initialization must explicitly reset optimizer/RNG and discard old rollout')
    model = PriorCandidateActorCritic(bundle['hidden'], **bundle['prior_config']).to(device)
    model.load_state_dict(bundle['state_dict'], strict=True)
    if float(model.prior_scale) != bundle['prior_config']['prior_scale']:
        raise ValueError('Prior scale mismatch')
    if not all(bool(torch.isfinite(value).all()) for value in model.state_dict().values()):
        raise ValueError('Nonfinite weight')
    return model.eval()


def load_checkpoint_bundle(path, device='cpu'):
    raw = Path(path).read_bytes()
    bundle = torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)
    return model_from_bundle(bundle, device), bundle, hashlib.sha256(raw).hexdigest()


def atomic_torch_save(data, path):
    model_from_bundle(data)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            torch.save(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def weights_bundle(model, lineage):
    return dict(format=PRIOR_FORMAT, schema=encoder.SCHEMA, encoder_version=ENCODER_VERSION,
        state_dim=STATE_DIM, candidate_dim=CANDIDATE_DIM, hidden=model.hidden,
        prior_config=dict(prior_scale=float(model.prior_scale), prior_feature_index=13),
        state_dict={key: value.detach().cpu().clone() for key, value in model.state_dict().items()},
        resume_supported=False, checkpoint_kind='weights_only_initialization',
        schema4_optimizer_steps=0, lineage=lineage)
