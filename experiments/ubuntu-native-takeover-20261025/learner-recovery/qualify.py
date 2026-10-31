"""Lease-gated real CUDA learner-only recovery; zero optimizer/native steps.

Root must acquire GPU then pool locks and launch this worker with inherited FDs.
This module never acquires its own replacement leases or starts a controller.
"""
import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
from pathlib import Path

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
HERE = Path(__file__).resolve().parent
CHECKPOINT_SHA = '5cd856b3221342c283899df126f4c50116d7779b3e0ea3b8d90125e243310354'
PREFIX_SHA = 'fd86a735a7e8597fd3329c999169dfb538cb484743b952bbced04f39751b0d16'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def resource(out, phase, initial=False):
    memory = {key:int(value.split()[0]) for key,value in
              (line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())}
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=temperature.gpu,memory.used',
                                   '--format=csv,noheader,nounits'], text=True).splitlines()[0].split(',')
    row = dict(phase=phase, available_mib=memory['MemAvailable']/1024,
               swap_mib=(memory['SwapTotal']-memory['SwapFree'])/1024,
               gpu_temperature=float(raw[0]), gpu_memory_mib=float(raw[1]))
    with (out/'RESOURCES.jsonl').open('a') as stream:
        stream.write(json.dumps(row) + '\n')
    assert row['available_mib'] > (4096 if initial else 2048)
    assert row['swap_mib'] < 256 and row['gpu_temperature'] < 86 and row['gpu_memory_mib'] < 14000


def profile_proof(path):
    certificate = json.loads(path.read_text())
    assert certificate['passed'] is True and certificate['wheel_record_audit_passed'] is True
    assert certificate['packages'] == 41
    assert Path(certificate['environment_root']).resolve() == Path(sys.prefix).resolve()
    audit_path = Path(certificate['audit_path'])
    assert sha(audit_path) == certificate['audit_sha256']
    audit = json.loads(audit_path.read_text())
    assert audit['passed'] is True and audit['distribution_count'] == 41
    assert Path(audit['venv']).resolve() == Path(sys.prefix).resolve()
    details_path = Path(certificate['details_path'])
    assert sha(details_path) == certificate['details_sha256'] == audit['details_sha256']
    assert sha(Path(certificate['requirements_path'])) == certificate['requirements_sha256']
    return dict(certificate_path=str(path.resolve()), certificate_sha256=sha(path),
                environment_root=str(Path(sys.prefix).resolve()), audit_sha256=certificate['audit_sha256'],
                all_41_installed_RECORD_checks_passed=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--profile-certificate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    result = dict(passed=False, optimizer_step_calls=0, native_games=0, DEV_rows_used=0,
                  model_promoted=False, final_test_touched=False)
    try:
        # No Torch import or CUDA initialization before real inherited leases pass.
        import leases
        lease_proof = leases.verify_pair()
        result['resource_lease'] = lease_proof
        result['Python_profile'] = profile_proof(args.profile_certificate)
        freeze = json.loads((HERE/'SOURCE_FREEZE.json').read_text())
        assert all(sha(HERE/path) == value for path,value in freeze['files'].items())
        assert sha(args.checkpoint) == CHECKPOINT_SHA
        assert sha(args.prefix) == PREFIX_SHA
        project = Path(os.environ['HEROES3_PROJECT_ROOT']).resolve()
        assert project == HERE.parents[2]
        sys.path.insert(0, str(project/'research'))
        import numpy as np
        import torch
        import full_graph_policy as graph
        import restore_learner_ubuntu as restore
        assert not torch.cuda.is_initialized()
        result['GPU_not_initialized_before_lease_verification'] = True
        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        resource(args.out, 'before_restore', True)
        model, cpu_optimizer, bundle, specification = restore.prepare(args.checkpoint, CHECKPOINT_SHA)
        assert (bundle['completed_updates'], bundle['actual_Adam_steps'], bundle['environment_steps']) == (62,7936,31744)
        assert bundle['terminal_credit_experiment']['arm'] == 'mc_fragment_lambda1'
        original_digest = restore.digest(bundle)
        original_model_digest = restore.digest(restore.weight_state(bundle))
        original_adam_digest = restore.digest(bundle['optimizer_state_dict'])
        count = dict(calls=0)
        def forbidden_step(*unused, **unused_kwargs):
            count['calls'] += 1
            raise AssertionError('Qualification must never call optimizer.step')
        cpu_optimizer.step = forbidden_step
        cpu_counter = restore.install_counter(cpu_optimizer)
        CPU = restore.restore_CPU(bundle, specification, model, cpu_optimizer, cpu_counter)
        CPU.pop('CUDA_rng_payload')
        assert cpu_counter['steps'] == 7936
        assert restore.digest(model.state_dict()) == original_model_digest
        assert restore.digest(cpu_optimizer.state_dict()) == original_adam_digest
        prefix = torch.load(args.prefix, map_location='cpu', weights_only=False)
        samples = prefix['raw']['samples'][:8]
        assert len(samples) == 8
        role_counts = {role:sum(sample['lab_side'] == side for sample in samples)
                       for side,role in enumerate(('attacker','defender'))}
        assert all(role_counts.values()), 'First eight TRAIN graphs must cover both roles'
        with torch.inference_mode():
            CPU_logits, CPU_values = model(*graph.collate(samples, 'cpu'))
            CPU_logits = CPU_logits.detach().clone()
            CPU_values = CPU_values.detach().clone()
        assert restore.digest(model.state_dict()) == original_model_digest
        model.cuda().eval()
        optimizer = restore.optimizer_for(model, bundle)
        optimizer.step = forbidden_step
        counter = restore.install_counter(optimizer, 7936)
        CUDA = restore.finalize_CUDA(bundle, specification, model, optimizer, counter)
        with torch.inference_mode():
            GPU_logits, GPU_values = model(*graph.collate(samples, 'cuda'))
            GPU_logits, GPU_values = GPU_logits.cpu(), GPU_values.cpu()
        torch.cuda.synchronize()
        mask = graph.collate(samples, 'cpu')[-1]
        torch.testing.assert_close(GPU_logits, CPU_logits, atol=2e-4, rtol=0.)
        torch.testing.assert_close(GPU_values, CPU_values, atol=2e-4, rtol=0.)
        NN = dict(TRAIN_graphs=8, roles=role_counts, source_prefix_sha256=PREFIX_SHA,
                  maximum_logit_error=float((GPU_logits[mask]-CPU_logits[mask]).abs().max()),
                  maximum_value_error=float((GPU_values-CPU_values).abs().max()), absolute_tolerance=2e-4,
                  relative_tolerance=0., passed=True)
        torch.save(dict(CPU_logits=CPU_logits, CPU_values=CPU_values, CUDA_logits=GPU_logits,
                        CUDA_values=GPU_values, mask=mask, source_prefix_sha256=PREFIX_SHA), args.out/'NN_COMPARISON.pt')
        def rng_payload():
            return dict(CPU=torch.get_rng_state(), CUDA=torch.cuda.get_rng_state_all(),
                        Python=random.getstate(), NumPy=restore.numpy_state_payload())
        saved_rng = dict(CPU=bundle['torch_rng_state'], CUDA=bundle['cuda_rng_states'],
                         Python=bundle['python_rng_state'], NumPy=bundle['numpy_rng_state'])
        def actual_draws():
            return dict(CPU=torch.rand(13), CUDA=torch.rand(13,device='cuda').cpu(),
                        Python=[random.random() for _ in range(5)], NumPy=np.random.rand(5))
        restore.restore_global_rng(bundle, specification, cuda=True)
        first = actual_draws()
        restore.restore_global_rng(bundle, specification, cuda=True)
        second = actual_draws()
        assert torch.equal(first['CPU'],second['CPU']) and torch.equal(first['CUDA'],second['CUDA'])
        assert first['Python'] == second['Python'] and np.array_equal(first['NumPy'],second['NumPy'])
        restore.restore_global_rng(bundle, specification, cuda=True)
        assert restore.digest(rng_payload()) == restore.digest(saved_rng)
        RNG = dict(passed=True, actual_CPU_draws=13, actual_CUDA_draws=13,
                   actual_Python_draws=5, actual_NumPy_draws=5,
                   repeated_draws_exact=True, original_full_rng_restored=True,
                   full_rng_digest=restore.digest(saved_rng))
        assert count['calls'] == 0 and counter['steps'] == 7936
        assert restore.digest(model.state_dict()) == original_model_digest
        assert restore.digest(optimizer.state_dict()) == original_adam_digest
        # Preserve every original metadata key; replace only learning payloads with
        # values captured from the restored live objects and restored global RNGs.
        captured = restore.clone(bundle)
        for role in ('attacker','defender'):
            captured['models'][role] = dict(weights={key.replace('__','.') : value.detach().cpu().clone()
                                                    for key,value in model.models[role].weights.items()},
                                           metadata=restore.clone(model.models[role].metadata))
        captured['optimizer_state_dict'] = restore.clone(optimizer.state_dict())
        captured['torch_rng_state'] = torch.get_rng_state().clone()
        captured['cuda_rng_states'] = [value.cpu().clone() for value in torch.cuda.get_rng_state_all()]
        captured['python_rng_state'] = random.getstate()
        captured['numpy_rng_state'] = restore.numpy_state_payload()
        captured['actual_Adam_steps'] = counter['steps']
        assert restore.digest(captured) == original_digest
        roundtrip = args.out/'zero-update-roundtrip.pt'
        temporary = args.out/'zero-update-roundtrip.tmp'
        with temporary.open('xb') as stream:
            torch.save(captured, stream)
            stream.flush()
            os.fsync(stream.fileno())
        assert not roundtrip.exists()
        os.replace(temporary, roundtrip)
        reload_bundle = torch.load(roundtrip, map_location='cpu', weights_only=True)
        assert restore.digest(reload_bundle) == original_digest
        restore.validate(reload_bundle, specification)
        del cpu_optimizer
        reload_model, reload_cpu_optimizer, reload_bundle, reload_specification = restore.prepare(roundtrip, sha(roundtrip))
        reload_cpu_optimizer.step = forbidden_step
        reload_cpu_counter = restore.install_counter(reload_cpu_optimizer)
        reload_CPU = restore.restore_CPU(reload_bundle, reload_specification, reload_model, reload_cpu_optimizer, reload_cpu_counter)
        reload_CPU.pop('CUDA_rng_payload')
        reload_model.cuda().eval()
        reload_optimizer = restore.optimizer_for(reload_model, reload_bundle)
        reload_optimizer.step = forbidden_step
        reload_counter = restore.install_counter(reload_optimizer,7936)
        reload_CUDA = restore.finalize_CUDA(reload_bundle,reload_specification,reload_model,reload_optimizer,reload_counter)
        assert restore.digest(reload_model.state_dict()) == original_model_digest
        assert restore.digest(reload_optimizer.state_dict()) == original_adam_digest
        assert restore.digest(rng_payload()) == restore.digest(saved_rng)
        assert reload_counter['steps'] == 7936 and count['calls'] == 0
        assert all(parameter.grad is None for parameter in reload_model.parameters())
        assert sha(args.checkpoint) == CHECKPOINT_SHA and sha(args.prefix) == PREFIX_SHA
        assert all(sha(HERE/path) == value for path,value in freeze['files'].items())
        resource(args.out,'after_roundtrip')
        result.update(passed=True, actual_Adam_steps=7936, completed_updates=62, environment_steps=31744,
                      optimizer_step_calls=count['calls'], CPU_restoration=CPU, CUDA_restoration=CUDA,
                      CPU_CUDA_NN_comparison=NN, four_RNG_actual_draw_recovery=RNG,
                      roundtrip_checkpoint=str(roundtrip.resolve()), roundtrip_sha256=sha(roundtrip),
                      complete_original_payload_digest=original_digest,
                      reload_complete_payload_digest=restore.digest(reload_bundle), full_payload_exact=True,
                      reloaded_CPU_restoration=reload_CPU,reloaded_CUDA_restoration=reload_CUDA,
                      model_digest=original_model_digest, named_Adam_digest=original_adam_digest,
                      original_checkpoint_unchanged=True, original_prefix_unchanged=True,
                      saved_metadata_unchanged=True, source_freeze_sha256=sha(HERE/'SOURCE_FREEZE.json'),
                      native_in_flight_state_restored=False,
                      scope='Zero-update learner-state migration qualification only. Canonical full-payload digests are exact; '
                            'serialization file bytes can differ. Eight archived TRAIN graphs exercise real CPU/CUDA inference. '
                            'No rollout continuation, training update, strength assessment, DEV use, or model promotion.')
    except BaseException as error:
        result['error'] = repr(error)
        raise
    finally:
        write(args.out/'RESULT.json', result)


if __name__ == '__main__':
    main()
