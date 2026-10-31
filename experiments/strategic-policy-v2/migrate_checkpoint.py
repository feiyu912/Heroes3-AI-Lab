#!/usr/bin/env python3
"""Explicit CPU-only v1 -> visible threat/supply weight migration; never optimizer resume."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import torch
from encoder import (SCHEMA, ENCODER_VERSION, STATE_DIM, CANDIDATE_DIM, LEGACY_STATE_DIM,
                     LEGACY_CANDIDATE_DIM, STATE_ADDED_FEATURES, CANDIDATE_ADDED_FEATURES, DISTANCE_CONVENTION)
from model import PRIOR_FORMAT, PriorCandidateActorCritic, atomic_torch_save, model_from_bundle

HERE = Path(__file__).resolve().parent


def migrate(path):
    raw = Path(path).read_bytes()
    parent_sha = hashlib.sha256(raw).hexdigest()
    old = torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True)
    if old.get('format') != 'strategic-candidate-prior-residual-v2' or old.get('encoder_version') != 'strategy-visible-encoder-v1':
        raise ValueError('Only explicit v1 prior-residual checkpoint migration is supported')
    new = PriorCandidateActorCritic(old['hidden'], **old['prior_config'])
    state = new.state_dict()
    if old['state_dict'].keys() != state.keys():
        raise ValueError('Legacy parameter names differ')
    for name, value in old['state_dict'].items():
        if name in ('actor.0.weight', 'critic.0.weight'):
            if value.shape != (old['hidden'], LEGACY_STATE_DIM + LEGACY_CANDIDATE_DIM):
                raise ValueError('Legacy first-layer dimensions differ')
            migrated = torch.zeros_like(state[name])
            migrated[:, :LEGACY_STATE_DIM] = value[:, :LEGACY_STATE_DIM]
            migrated[:, STATE_DIM:STATE_DIM+LEGACY_CANDIDATE_DIM] = value[:, LEGACY_STATE_DIM:]
            state[name] = migrated
        else:
            if state[name].shape != value.shape:
                raise ValueError('Non-input parameter shape differs: '+name)
            state[name] = value.clone()
    new.load_state_dict(state, strict=True)
    recipe = dict(schema='strategic-threat-supply-weight-migration-v1', request_schema=SCHEMA,
        encoder_version=ENCODER_VERSION, model_format=PRIOR_FORMAT, state_dim=STATE_DIM, candidate_dim=CANDIDATE_DIM,
        appended_state_features=list(STATE_ADDED_FEATURES), appended_candidate_features=list(CANDIDATE_ADDED_FEATURES),
        first_layer_mapping=dict(old_state=f'old[:,:{LEGACY_STATE_DIM}] -> new[:,:{LEGACY_STATE_DIM}]',
            old_candidates=f'old[:,{LEGACY_STATE_DIM}:] -> new[:,{STATE_DIM}:{STATE_DIM+LEGACY_CANDIDATE_DIM}]',
            new_feature_weights='All zero; no heuristic preference injected'),
        distance_convention=DISTANCE_CONVENTION, source_sha256={str(HERE/name): hashlib.sha256((HERE/name).read_bytes()).hexdigest()
            for name in ('encoder.py', 'model.py', 'migrate_checkpoint.py')})
    bundle = dict(format=PRIOR_FORMAT, encoder_version=ENCODER_VERSION, hidden=new.hidden,
        state_dim=STATE_DIM, candidate_dim=CANDIDATE_DIM, prior_config=old['prior_config'],
        state_dict={name: value.detach().cpu().clone() for name, value in new.state_dict().items()},
        training_updates=0, optimizer_steps_total=0, optimizer=None, complete_update_boundary=False,
        trained=bool(old.get('trained', False) or old.get('training_updates', 0)),
        weights_only_initialization=True, value_is_win_probability=False,
        lineage=dict(mode='explicit-v1-to-v2-visible-weight-migration', parent_checkpoint=str(Path(path).resolve()),
            parent_sha256=parent_sha, parent_training_updates=int(old.get('training_updates', 0)),
            parent_lineage=old.get('lineage'), parent_protocol_sha256=old.get('protocol_sha256'),
            parent_optimizer_steps_total=old.get('optimizer_steps_total'),
            reset_optimizer=True, reset_rng=True, source_optimizer_reused=False),
        migration_protocol=recipe, migration_protocol_sha256=hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest(),
        scope='Visible target choice; extra threat/supply columns initially zero. No trained use of new information yet.')
    model_from_bundle(bundle)
    return bundle


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path, help='New checkpoint path; existing files refused')
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Refusing to overwrite a checkpoint')
    if args.source.resolve() == args.out.resolve():
        parser.error('Migration must not modify parent checkpoint')
    torch.set_num_threads(1)
    bundle = migrate(args.source)
    atomic_torch_save(bundle, args.out)
    print(json.dumps(dict(path=str(args.out), lineage=bundle['lineage'],
        sha256=hashlib.sha256(args.out.read_bytes()).hexdigest(), migration_protocol_sha256=bundle['migration_protocol_sha256'])))


if __name__ == '__main__':
    main()
