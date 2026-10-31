#!/usr/bin/env python3
"""CPU-only numerical migration and broker IO checks; synthetic, no game results."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

import torch
from torch.distributions import Categorical

import encoder
from legacy import load_legacy_checkpoint
from migrate_checkpoint import migrate
from model import atomic_torch_save, load_checkpoint_bundle, model_from_bundle

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--parent', type=Path, default=HERE.parent / 'strategic-policy-v1/takeover-03/native-boundary-01/continuous-2/update-2.pt')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    torch.random.default_generator.manual_seed(2026101831)
    original_parent_sha = hashlib.sha256(args.parent.read_bytes()).hexdigest()
    fixture = json.loads((HERE / 'fixtures/visible-request.json').read_text())
    request2 = copy.deepcopy(fixture)
    request2.update(request_id=2, visible_threats=[], own_towns=[], candidates=fixture['candidates'][:1])
    requests = [fixture, request2]
    data = migrate(args.parent)
    model = model_from_bundle(data)
    old_model, old_collate, old_sha = load_legacy_checkpoint(args.parent)
    assert old_sha == original_parent_sha == data['lineage']['parent_sha256']
    old_encoded, encoded = old_collate(requests), encoder.collate(requests)
    assert torch.equal(encoded['state'][:, :11], old_encoded['state'])
    assert torch.equal(encoded['candidates'][:, :, :15], old_encoded['candidates'])
    assert torch.equal(encoded['mask'], old_encoded['mask'])
    assert encoded['state'].shape[-1] == 26 and encoded['candidates'].shape[-1] == 23
    for group in ('actor', 'critic'):
        weight = data['state_dict'][group+'.0.weight']
        old = old_model.state_dict()[group+'.0.weight']
        assert torch.equal(weight[:, :11], old[:, :11])
        assert torch.equal(weight[:, 26:41], old[:, 11:26])
        assert not bool(weight[:, 11:26].ne(0).any()) and not bool(weight[:, 41:].ne(0).any())
    with torch.no_grad():
        old_logits, old_values = old_model(**old_encoded)
        logits, values = model(**encoded)
    mask = encoded['mask']
    logit_error = float((old_logits[mask]-logits[mask]).abs().max())
    value_error = float((old_values-values).abs().max())
    assert torch.allclose(old_logits[mask], logits[mask], atol=2e-6, rtol=1e-5)
    assert torch.allclose(old_values, values, atol=2e-6, rtol=1e-5)
    assert torch.isneginf(logits[~mask]).all() and Categorical(logits=logits).probs[~mask].eq(0).all()
    changed = copy.deepcopy(fixture)
    changed['visible_threats'][0]['position'] = [30, 30, 0]
    changed['own_towns'][0]['army_value'] = 50
    before_state, before_cands = encoder.encode(fixture)
    after_state, after_cands = encoder.encode(changed)
    assert before_state[:11] == after_state[:11] and before_state[11:] != after_state[11:]
    assert before_cands[0][:15] == after_cands[0][:15] and before_cands[0][15:] != after_cands[0][15:]
    with torch.no_grad():
        changed_logits, changed_values = model(**encoder.collate([changed]))
        original_logits, original_values = model(**encoder.collate([fixture]))
    assert torch.equal(changed_logits, original_logits) and torch.equal(changed_values, original_values)
    state_names = {name: 11+index for index, name in enumerate(encoder.STATE_ADDED_FEATURES)}
    cand_names = {name: 15+index for index, name in enumerate(encoder.CANDIDATE_ADDED_FEATURES)}
    assert before_state[state_names['max_enemy_to_hero_army_logratio']] > 0
    assert before_cands[0][cand_names['target_own_garrison_to_hero_logratio']] > before_cands[1][cand_names['target_own_garrison_to_hero_logratio']]
    assert before_cands[1][cand_names['target_visible_enemy_pressure']] > before_cands[0][cand_names['target_visible_enemy_pressure']]
    invalids = []
    for field in ('visible_threats', 'own_towns'):
        bad = copy.deepcopy(fixture)
        bad.pop(field)
        invalids.append(bad)
    bad = copy.deepcopy(fixture)
    bad['schema'] = 'strategy-candidates-v2'
    invalids.append(bad)
    bad = copy.deepcopy(fixture)
    bad['visible_threats'][0]['approx_army_value'] = float('nan')
    invalids.append(bad)
    for bad in invalids:
        try:
            encoder.validate(bad)
        except ValueError:
            pass
        else:
            raise AssertionError('Missing/malformed visible information silently accepted')
    model.zero_grad(set_to_none=True)
    logits, values = model(**encoded)
    loss = -Categorical(logits=logits).log_prob(torch.tensor([0, 0])).mean() + values.square().mean()
    loss.backward()
    gradients = {}
    for group in ('actor', 'critic'):
        gradient = getattr(model, group)[0].weight.grad
        assert torch.isfinite(gradient).all()
        gradients[group] = dict(appended_state_gradient_l1=float(gradient[:, 11:26].abs().sum()),
                                appended_candidate_gradient_l1=float(gradient[:, 41:].abs().sum()))
        assert all(value > 0 for value in gradients[group].values())
    checkpoint = args.out / 'migrated-test.pt'
    atomic_torch_save(data, checkpoint)
    reloaded, reloaded_bundle, checkpoint_sha = load_checkpoint_bundle(checkpoint)
    assert all(torch.equal(value, reloaded.state_dict()[name]) for name, value in model.state_dict().items())
    assert reloaded_bundle['optimizer'] is None and reloaded_bundle['optimizer_steps_total'] == 0
    # This is file-protocol traffic only: no runner or native process is invoked.
    modes = ['heuristic', 'legacy-policy', 'new-policy']
    if (HERE / 'supply_policy.py').exists():
        modes.append('supply-aware')
    brokers = {}
    for mode in modes:
        directory = args.out / ('broker-'+mode)
        directory.mkdir()
        for index, request in enumerate(requests, 1):
            (directory / f'request-{index:08d}.json').write_text(json.dumps(request))
        bad = dict(fixture, request_id=3)
        bad.pop('visible_threats')
        (directory / 'request-00000003.json').write_text(json.dumps(bad))
        source = args.parent if mode in ('legacy-policy', 'supply-aware') else checkpoint
        command = [sys.executable, str(HERE / 'broker.py'), '--mode', mode, '--agent-dir', str(directory),
                   '--max-requests', '3', '--idle-seconds', '5']
        if mode != 'heuristic':
            command += ['--checkpoint', str(source)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                                env=dict(os.environ, CUDA_VISIBLE_DEVICES=''))
        (directory / 'process.log').write_text(result.stdout+result.stderr)
        assert result.returncode == 0, result.stderr
        assert (directory / 'action-00000001.json').exists() and (directory / 'action-00000002.json').exists()
        assert not (directory / 'action-00000003.json').exists() and (directory / 'error-00000003.json').exists()
        ready = json.loads((directory / 'broker-ready.json').read_text())
        brokers[mode] = dict(actions=[int((directory / f'action-{index:08d}.json').read_text()) for index in (1, 2)],
                             model_scope=ready['model_scope'], invalid_missing_field_rejected=True)
    assert brokers['legacy-policy']['actions'] == brokers['new-policy']['actions']
    # Exercise actual trainer's CPU-only setup; hard-fail any CUDA RNG use.
    import train_ppo_pilot as trainer
    no_cuda = lambda *a, **kw: (_ for _ in ()).throw(AssertionError('CPU preflight touched CUDA RNG'))
    with patch.object(torch.cuda, 'get_rng_state_all', no_cuda), patch.object(torch.cuda, 'set_rng_state_all', no_cuda), \
         patch.object(sys, 'argv', ['train_ppo_pilot.py', '--out', str(args.out/'trainer-preflight'), '--preflight',
                                  '--initialize-from', str(checkpoint)]):
        assert trainer.main() == 0
    assert not torch.cuda.is_initialized()
    assert hashlib.sha256(args.parent.read_bytes()).hexdigest() == original_parent_sha
    snapshot = args.out / 'sources'
    snapshot.mkdir()
    paths = [path for path in HERE.glob('*.py')]
    for path in paths:
        shutil.copy2(path, snapshot/path.name)
    report = dict(passed=True, game_started=False, GPU_initialized=False, optimizer_steps=0,
        state_dim=26, candidate_dim=23, parent_sha256=old_sha, migrated_checkpoint_sha256=checkpoint_sha,
        parent_lineage=data['lineage'], numerical_error=dict(logit_max_abs=logit_error, value_max_abs=value_error),
        extra_columns_zero=True, extra_information_changes_features=True, extra_information_initially_does_not_change_policy=True,
        legacy_prefix_and_mask_preserved=True, invalid_observations_rejected=len(invalids),
        finite_nonzero_extra_feature_gradients=gradients, broker_checks=brokers,
        trainer_CPU_preflight_passed=True, source_sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        limitations='Synthetic CPU engineering checks only; native visibility provenance and strategic benefit require real-game validation.')
    (args.out / 'AUDIT.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
