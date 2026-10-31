"""Explicit CPU weights-only migration from the registered schema3 update-2 parent."""
import argparse
import hashlib
import importlib.util
import io
from pathlib import Path

import torch

PARENT_SHA256 = '9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159'
ROOT = Path(__file__).resolve().parent


def load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


typed = load_file('_isolated_schema4_model', ROOT / 'model.py')


def migrate(parent):
    raw = Path(parent).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != PARENT_SHA256:
        raise ValueError('Only registered schema3 update-2 parent is authorized by this migration recipe')
    old = torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)
    if (old.get('format') != 'strategic-visible-threat-supply-prior-v3' or old.get('state_dim') != 26
            or old.get('candidate_dim') != 23 or old.get('encoder_version') != 'strategy-visible-threat-supply-encoder-v2'):
        raise ValueError('Unexpected parent model/encoder format')
    model = typed.PriorCandidateActorCritic(old['hidden'], **old['prior_config'])
    state = model.state_dict()
    expected = set(state) - {'actor.stop_bias'}
    if set(old['state_dict']) != expected:
        raise ValueError('Parent weights differ from migration contract')
    for key, value in old['state_dict'].items():
        if not bool(torch.isfinite(value).all()):
            raise ValueError('Nonfinite parent weight')
        if key in ('actor.0.weight', 'critic.0.weight'):
            if value.shape[1] != 49:
                raise ValueError('Unexpected legacy first-layer width')
            state[key].zero_()
            state[key][:, :26] = value[:, :26]
            state[key][:, 27:50] = value[:, 26:49]
        else:
            if state[key].shape != value.shape:
                raise ValueError('Unexpected parent tensor shape')
            state[key].copy_(value)
    model.load_state_dict(state, strict=True)
    lineage = dict(parent_path=str(Path(parent).resolve()), parent_sha256=digest,
        parent_format=old['format'], parent_lineage=old.get('lineage'),
        parent_trained=old.get('trained'), parent_training_updates=old.get('training_updates'),
        recipe='schema3_state26_candidate23_to_schema4_state27_candidate25_zero_new_columns_v1',
        reset_optimizer=True, reset_rng=True, discard_rollout=True,
        weights_only=True, stop_bias_engineering_prior=-4., stop_prior_is_learned=False)
    return model.eval(), typed.weights_bundle(model, lineage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Refuse overwrite')
    model, bundle = migrate(args.parent)
    typed.atomic_torch_save(bundle, args.out)
    print(f'Saved typed weights-only initialization: {args.out}')


if __name__ == '__main__':
    main()
