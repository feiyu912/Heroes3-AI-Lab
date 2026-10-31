"""Independent read-only recovery audit for the stopped control-phase-1.

This audits the old stage without modifying it and writes only to --out. It
does not start native workers, use CUDA, or run an optimizer. Passing this
audit accepts update-64 only as a starting boundary; it does not retroactively
turn the old failed stage into a passed official stage.
"""
import argparse
import hashlib
import json
import sys
import traceback
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
R = ROOT / 'research'
GYM = Path('/root/heroes3-ai-lab/src/gym')
sys.path[:0] = [str(HERE), str(R), str(GYM)]

import numpy as np
import torch

import audit
import restore_learner as restore
import targets


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def boundary(path, expected_sha):
    model, opt, bundle, spec = restore.prepare(Path(path), expected_sha)
    counter = restore.install_counter(opt)
    proof = restore.restore_CPU(bundle, spec, model, opt, counter)
    return bundle, counter, proof


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    report = dict(
        schema='terminal-credit-recovery-audit-v1',
        passed=False,
        accepted_for_recovery=False,
        not_an_official_stage_audit=True,
        stage=str(a.stage),
        source_sha256=sha(__file__),
        audit_source_sha256=sha(HERE / 'audit.py'),
        targets_source_sha256=sha(HERE / 'targets.py'),
        restore_source_sha256=sha(HERE / 'restore_learner.py'),
        new_native_games=0,
        GPU_operations=0,
        optimizer_steps=0,
    )
    try:
        torch.set_num_threads(1)
        result_path = a.stage / 'RESULT.json'
        progress_path = a.stage / 'PROGRESS.json'
        log_path = a.stage.parent / (a.stage.name + '.log')
        d = json.loads(result_path.read_text())
        progress = json.loads(progress_path.read_text())
        assert d['passed'] is False
        assert d['error'] == 'AssertionError()'
        assert d['arm'] == 'control'
        assert d['partial_native_not_restorable'] is True
        assert d['actual_Adam_steps'] == 8192
        assert [r['update'] for r in d['records']] == [63]
        assert [r['update'] for r in progress['records']] == [63]
        assert not (a.stage / 'AUDIT.json').exists()
        assert Path(d['checkpoint']).name == 'update-64.pt'
        assert d.get('checkpoint_sha256') is None

        folder = a.stage / 'phase-1'
        workers = json.loads((folder / 'WORKERS.json').read_text())
        registered = json.loads((HERE / 'REGISTERED_CURRICULUM.json').read_text())['phases'][1]
        assert len(set(workers['worker_PIDs'])) == 16
        assert all(pid > 0 for pid in workers['worker_PIDs'])
        assert workers['torch_imported'] == [False] * 16
        for cfg, row in zip(workers['configs'], registered):
            assert all(cfg[name] == row[name] for name in ['map', 'role', 'opponent', 'seed', 'family'])
            assert cfg['TRAIN_scenario_index'] == row['scenario_index']
            assert cfg['initial_reset_once'] and cfg['step_cost'] == 0

        p0, next0, c0, f0 = audit.raw_check(folder / 'admitted-0.pt', 32, True)
        p1, next1, c1, f1 = audit.raw_check(folder / 'admitted-1.pt', 32, True, next0)
        suffix, nexts, cs, fs = audit.raw_check(folder / 'suffix.pt', 64, False, next1)
        assert p1['behavior_checkpoint_sha256'] == suffix['behavior_checkpoint_sha256']

        saved_path = folder / 'TARGETS.pt'
        saved = audit.payload(saved_path)
        recomputed = targets.build(p1['arrays'], suffix['arrays'], 'control')
        for key in ['advantage', 'returns', 'base_advantage', 'base_returns',
                    'candidate_advantage', 'candidate_returns', 'eligible']:
            assert np.array_equal(recomputed[key], saved['targets'][key]), key
        assert saved['targets']['reason'] == recomputed['reason']
        assert saved['global_RNG_unchanged']
        assert saved['learning_RNG_before_suffix'] == saved['learning_RNG_after_suffix']
        assert len(saved['private_sampling_RNG_before']) == len(saved['private_sampling_RNG_after']) == 16
        for kind in ['prefix', 'suffix']:
            ev = saved[kind]
            assert restore.sha(ev['path']) == ev['sha256']

        record63 = d['records'][0]
        assert record63['actual_Adam'] == 128
        assert record63['cumulative_Adam'] == 8064
        assert Path(suffix['behavior_checkpoint']) == Path(record63['checkpoint'])
        assert suffix['behavior_checkpoint_sha256'] == record63['checkpoint_sha256']
        behavior = torch.load(suffix['behavior_checkpoint'], map_location='cpu', weights_only=True)
        assert restore.digest(restore.weight_state(behavior)) == saved['behavior_model_digest'] == saved['behavior_model_after_suffix']
        assert restore.digest(behavior['optimizer_state_dict']) == saved['Adam_digest'] == saved['Adam_after_suffix']

        b63, counter63, proof63 = boundary(record63['checkpoint'], record63['checkpoint_sha256'])
        assert b63['completed_updates'] == 63
        assert b63['environment_steps'] == 32256
        assert b63['actual_Adam_steps'] == 8064
        assert b63['terminal_credit_experiment']['phase_complete'] is False

        cp64 = a.stage / 'update-64.pt'
        sha64 = sha(cp64)
        b64, counter64, proof64 = boundary(cp64, sha64)
        assert b64['completed_updates'] == 64
        assert b64['environment_steps'] == 32768
        assert b64['actual_Adam_steps'] == 8192
        assert counter64['steps'] == 8192
        meta64 = b64['terminal_credit_experiment']
        assert meta64['arm'] == 'control' and meta64['phase'] == 1 and meta64['half'] == 1
        assert meta64['phase_complete'] is True
        assert meta64['parent60_sha256'] == restore.DEFAULT_SHA
        assert meta64['admitted_stage_rows'] == 2048
        assert meta64['suffix_stage_rows'] == 2048
        assert meta64['total_native_stage_rows'] == 4096
        assert meta64['target_evidence']['path'] == str(saved_path)
        assert meta64['target_evidence']['sha256'] == sha(saved_path)
        assert meta64['prefix_rollout']['sha256'] == sha(folder / 'admitted-1.pt')
        assert b64['rollout_evidence']['sha256'] == sha(folder / 'admitted-1.pt')
        assert b64['rollout_evidence']['path'] == str(folder / 'admitted-1.pt')

        frozen = b64['frozen_inputs']['input_sha256']
        frozen_missing = [path for path in frozen if not Path(path).exists()]
        frozen_mismatch = [path for path, expected in frozen.items()
                           if Path(path).exists() and sha(path) != expected]
        assert not frozen_missing and not frozen_mismatch

        eligible = int(np.sum(recomputed['eligible']))
        assert eligible >= 1
        report.update(
            passed=True,
            accepted_for_recovery=True,
            stage_result_sha256=sha(result_path),
            stage_progress_sha256=sha(progress_path),
            stage_log_sha256=sha(log_path),
            stage_audit_exists=False,
            recorded_updates=[63],
            update_63_sha256=record63['checkpoint_sha256'],
            update_64_sha256=sha64,
            update_64_bytes=cp64.stat().st_size,
            targets_sha256=sha(saved_path),
            raw=dict(
                prefix_rows=c0['rows'] + c1['rows'],
                suffix_rows=cs['rows'],
                prefix_terminations=c0['terminals'] + c1['terminals'],
                suffix_terminations=cs['terminals'],
                journal_files=len(f0 + f1 + fs),
            ),
            eligible_workers=eligible,
            reasons=list(recomputed['reason']),
            frozen_inputs_checked=len(frozen),
            frozen_inputs_missing=frozen_missing,
            frozen_inputs_mismatch=frozen_mismatch,
            boundary_63=dict(completed_updates=b63['completed_updates'],
                             environment_steps=b63['environment_steps'],
                             actual_Adam_steps=b63['actual_Adam_steps']),
            boundary_64=dict(completed_updates=b64['completed_updates'],
                             environment_steps=b64['environment_steps'],
                             actual_Adam_steps=b64['actual_Adam_steps'],
                             phase_complete=meta64['phase_complete']),
            accepted_boundary_sha256=sha64,
            acceptance_scope='starting boundary only; original stage remains failed',
        )
    except BaseException as error:
        report.update(passed=False, accepted_for_recovery=False,
                      error=repr(error), traceback=traceback.format_exc())
        raise
    finally:
        (a.out / 'RECOVERY_AUDIT.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
