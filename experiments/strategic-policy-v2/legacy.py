"""Explicit legacy observation projection for controlled same-native baselines."""
import hashlib
import importlib.util
import io
from pathlib import Path
import sys

import torch
from encoder import legacy_projection

LEGACY_DIR = Path(__file__).resolve().parent.parent / 'strategic-policy-v1'


def legacy_modules():
    def read_module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    encoder = read_module('_strategic_legacy_encoder', LEGACY_DIR / 'encoder.py')
    previous = sys.modules.get('encoder')
    try:
        sys.modules['encoder'] = encoder
        model = read_module('_strategic_legacy_model', LEGACY_DIR / 'model.py')
    finally:
        if previous is None:
            sys.modules.pop('encoder', None)
        else:
            sys.modules['encoder'] = previous
    return encoder, model


def load_legacy_checkpoint(path):
    raw = Path(path).read_bytes()
    bundle = torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)
    encoder, module = legacy_modules()
    if bundle.get('format') != module.PRIOR_FORMAT or bundle.get('encoder_version') != encoder.ENCODER_VERSION:
        raise ValueError('legacy-policy requires an explicit v1 prior checkpoint; no random/model fallback')
    model = module.PriorCandidateActorCritic(bundle['hidden'], **bundle['prior_config'])
    model.load_state_dict(bundle['state_dict'], strict=True)
    if not all(bool(torch.isfinite(value).all()) for value in model.state_dict().values()):
        raise ValueError('Nonfinite legacy model weight')
    if float(model.prior_scale) != bundle['prior_config']['prior_scale']:
        raise ValueError('Legacy prior scale/state disagreement')
    def collate_legacy(requests):
        return encoder.collate([legacy_projection(request) for request in requests], 'cpu')
    return model.eval(), collate_legacy, hashlib.sha256(raw).hexdigest()
