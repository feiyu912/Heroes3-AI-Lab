#!/usr/bin/env python3
"""CPU-only checkpoint engineering checks; synthetic samples are not game results."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile
from unittest.mock import patch

import torch
from torch.distributions import Categorical

import train_ppo_pilot as trainer


def identical(a, b):
    if isinstance(a, torch.Tensor):
        return isinstance(b, torch.Tensor) and torch.equal(a, b)
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(identical(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)):
        return type(a) is type(b) and len(a) == len(b) and all(identical(x, y) for x, y in zip(a, b))
    return a == b


def synthetic_samples(model, count=70):
    rows = []
    for i in range(count):
        request = dict(schema='strategy-candidates-v2', request_id=i + 1, player=i % 2,
                       day=i % 7 + 1, hero=1, gold=1000 + i * 10, wood=10, ore=10,
                       own_army_value=500, movement=1000, **{'from': [1, 1, 0]},
                       candidates=[dict(kind=kind, position=[x, 2, 0], next=[2, 1, 0],
                                        path_cost=100, heuristic_score=score)
                                   for kind, x, score in [(0, 4, .1), (5, 5, -.1)]])
        with torch.no_grad():
            logits, values = model(**trainer.collate([request]))
            distribution = Categorical(logits=logits[0])
            action = distribution.sample()
        rows.append(dict(request=request, action=int(action), old_logprob=float(distribution.log_prob(action)),
                         old_value=float(values[0]), **{'return': 1.0 if i % 3 else -1.0}))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    snapshot = args.out / 'sources'
    snapshot.mkdir()
    for path in (Path(__file__), Path(trainer.__file__), trainer.HERE / 'encoder.py', trainer.HERE / 'model.py'):
        shutil.copy2(path, snapshot / path.name)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.random.default_generator.manual_seed(12345)
    random.seed(12345)
    initial = trainer.HERE / 'checkpoints/prior-initial-v2.pt'
    old = trainer.HERE / 'ppo-pilot-02/update-2.pt'
    checks = {}
    device = torch.device('cpu')
    no_cuda = lambda *a, **kw: (_ for _ in ()).throw(AssertionError('CPU check touched CUDA RNG'))
    with patch.object(torch.cuda, 'get_rng_state_all', no_cuda), patch.object(torch.cuda, 'set_rng_state_all', no_cuda):
        model, _, _ = trainer.read_checkpoint(initial)
        optimizer = torch.optim.Adam(model.parameters(), lr=.0003)
        before = trainer.parameter_snapshot(model)
        first = trainer.ppo_update(model, optimizer, synthetic_samples(model), device)
        delta = trainer.parameter_delta(model, before)
        assert all(delta[g]['changed_tensors'] > 0 for g in ('actor', 'critic'))
        assert trainer.optimizer_steps(optimizer) == first['optimizer_steps'] > 0
        checks['first_synthetic_update'] = dict(metrics=first, delta=delta)
        boundary = args.out / 'synthetic-boundary.pt'
        trainer.save_model(model, optimizer, boundary, 1, 'synthetic-plan', 'synthetic-protocol')
        saved_raw = boundary.read_bytes()
        saved_rng = torch.get_rng_state().clone()
        saved_python_rng = random.getstate()

        # Continuous update 2 includes stochastic actions and a shuffled minibatch order.
        continuous_metrics = trainer.ppo_update(model, optimizer, synthetic_samples(model), device)
        continuous_model = copy.deepcopy(model.state_dict())
        continuous_optimizer = copy.deepcopy(optimizer.state_dict())
        continuous_rng = torch.get_rng_state().clone()
        continuous_python_draw = random.random()

        # Restore in a fresh model and optimizer, including RNG after model construction.
        restored, bundle, digest = trainer.read_checkpoint(boundary)
        pristine_bundle = copy.deepcopy(bundle)
        restored_optimizer = torch.optim.Adam(restored.parameters(), lr=.0003)
        start, steps = trainer.restore_boundary(bundle, restored_optimizer, device, 'synthetic-protocol', 2)
        assert start == 1 and steps == first['optimizer_steps']
        assert torch.equal(torch.get_rng_state(), saved_rng) and random.getstate() == saved_python_rng
        resumed_metrics = trainer.ppo_update(restored, restored_optimizer, synthetic_samples(restored), device)
        assert identical(continuous_model, restored.state_dict())
        assert identical(continuous_optimizer, restored_optimizer.state_dict())
        assert continuous_metrics == resumed_metrics
        assert torch.equal(torch.get_rng_state(), continuous_rng)
        assert random.random() == continuous_python_draw
        checks['synthetic_boundary_resume_bitwise_equal'] = dict(passed=True, model=True, optimizer=True,
                                                                 cpu_rng=True, python_rng=True,
                                                                 steps_total=trainer.optimizer_steps(restored_optimizer))

        # File replacement after its only read cannot mix model and optimizer bytes.
        original_read = Path.read_bytes
        reads = []
        def replace_after_read(path):
            raw = original_read(path)
            if path == boundary:
                reads.append(path)
                path.write_bytes(b'replaced-after-single-read')
            return raw
        with patch.object(Path, 'read_bytes', replace_after_read):
            once_model, once_bundle, once_digest = trainer.read_checkpoint(boundary)
        assert len(reads) == 1 and once_digest == hashlib.sha256(saved_raw).hexdigest() == digest
        assert identical(once_model.state_dict(), bundle['state_dict'])
        assert identical(once_bundle['optimizer'], pristine_bundle['optimizer'])
        boundary.write_bytes(saved_raw)
        checks['single_read_sha_and_restore'] = True

        # Failed serialization must retain the previous checkpoint without leftovers.
        def interrupted_save(data, stream):
            stream.write(b'incomplete')
            raise OSError('injected serialization failure')
        with patch.object(torch, 'save', interrupted_save):
            try:
                trainer.save_model(restored, restored_optimizer, boundary, 2, 'plan', 'protocol')
            except OSError:
                pass
            else:
                raise AssertionError('Injected save failure did not propagate')
        assert boundary.read_bytes() == saved_raw and not list(args.out.glob('*.tmp'))
        checks['atomic_save_failure_retains_previous'] = True

        # An exception after an actual step is counted from optimizer state even
        # when the callback did not return. This matches main's failure accounting.
        failed, _, _ = trainer.read_checkpoint(initial)
        failed_optimizer = torch.optim.Adam(failed.parameters(), lr=.0003)
        rows = synthetic_samples(failed)
        step = failed_optimizer.step
        calls = 0
        def fail_after_step(*a, **kw):
            nonlocal calls
            result = step(*a, **kw)
            calls += 1
            if calls == 3:
                raise RuntimeError('injected failure after third actual optimizer step')
            return result
        progress = {}
        with patch.object(failed_optimizer, 'step', fail_after_step):
            try:
                trainer.ppo_update(failed, failed_optimizer, rows, device, progress)
            except RuntimeError as error:
                assert 'injected' in str(error)
            else:
                raise AssertionError('Injected update failure did not propagate')
        assert trainer.optimizer_steps(failed_optimizer) == 3 and progress['optimizer_steps'] == 2
        partial = args.out / 'synthetic-failed-partial.pt'
        trainer.save_model(failed, failed_optimizer, partial, 0, 'plan', 'synthetic-protocol', False)
        _, partial_bundle, _ = trainer.read_checkpoint(partial)
        try:
            trainer.restore_boundary(partial_bundle, torch.optim.Adam(failed.parameters()), device,
                                     'synthetic-protocol', 2)
        except ValueError as error:
            assert 'complete-update boundary' in str(error)
        else:
            raise AssertionError('Partial checkpoint was accepted for resume')
        checks['partial_failure_actual_optimizer_steps'] = dict(actual_steps=3, callback_completed_steps=2,
                                                               partial_rejected_for_resume=True)
        mismatch_optimizer = torch.optim.Adam(failed.parameters())
        for kind, altered in [('protocol', dict(pristine_bundle, protocol_sha256='wrong')),
                              ('step_metadata', dict(pristine_bundle, optimizer_steps_total=-1))]:
            try:
                trainer.restore_boundary(altered, mismatch_optimizer, device, 'synthetic-protocol', 2)
            except ValueError:
                checks[kind + '_mismatch_rejected'] = True
            else:
                raise AssertionError(kind + ' mismatch accepted')
        old_model, old_bundle, old_digest = trainer.read_checkpoint(old)
        fresh_optimizer = torch.optim.Adam(old_model.parameters(), lr=.0003)
        assert trainer.optimizer_steps(fresh_optimizer) == 0 and not fresh_optimizer.state
        checks['historical_update2_readonly_load'] = dict(sha256=old_digest,
            training_updates=old_bundle['training_updates'],
            historical_optimizer_steps=max(int(s['step']) for s in old_bundle['optimizer']['state'].values()),
            weights_only_migration_optimizer_steps=trainer.optimizer_steps(fresh_optimizer))
        checks['cpu_no_cuda_rng_access'] = True

    assert not torch.cuda.is_initialized()
    # Exercise the real CLI's migration preflight, in this same no-CUDA process.
    cli_out = args.out / 'migration-preflight'
    with patch.object(torch.cuda, 'get_rng_state_all', no_cuda), patch.object(torch.cuda, 'set_rng_state_all', no_cuda), \
         patch.object(sys, 'argv', ['train_ppo_pilot.py', '--out', str(cli_out), '--preflight',
                                  '--initialize-from', str(old)]):
        assert trainer.main() == 0
    preflight = json.loads((cli_out / 'preflight.json').read_text())
    assert preflight['lineage']['parent_sha256'] == old_digest
    assert preflight['optimizer_steps'] == 0 and not torch.cuda.is_initialized()
    checks['real_cli_migration_cpu_preflight'] = preflight
    recipe = json.loads((cli_out / 'protocol.json').read_text())
    resume_checkpoint = args.out / 'synthetic-cli-resume-boundary.pt'
    trainer.save_model(restored, restored_optimizer, resume_checkpoint, 1, 'synthetic-plan', recipe['sha256'],
                       protocol=recipe['protocol'])
    resume_out = args.out / 'resume-preflight'
    with patch.object(torch.cuda, 'get_rng_state_all', no_cuda), patch.object(torch.cuda, 'set_rng_state_all', no_cuda), \
         patch.object(sys, 'argv', ['train_ppo_pilot.py', '--out', str(resume_out), '--preflight',
                                  '--updates', '2', '--resume', str(resume_checkpoint)]):
        assert trainer.main() == 0
    resumed_preflight = json.loads((resume_out / 'preflight.json').read_text())
    assert resumed_preflight['optimizer_steps_total'] == 16 and not torch.cuda.is_initialized()
    checks['real_cli_resume_cpu_preflight'] = resumed_preflight
    report = dict(passed=True, device='cpu', game_started=False, GPU_initialized=False,
                  scope='Synthetic checkpoint engineering only. No native-game boundary replay or ability claim.',
                  trainer_sha256=trainer.sha(Path(trainer.__file__)),
                  audit_script_sha256=trainer.sha(Path(__file__)), checks=checks)
    trainer.atomic_json(args.out / 'AUDIT.json', report)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
