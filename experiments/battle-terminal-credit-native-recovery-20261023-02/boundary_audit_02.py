"""Read-only boundary acceptance for recovery-02 from both update-66 checkpoints."""
import argparse
import hashlib
import json
import shutil
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
R = ROOT / 'research'
TRAIN = ROOT / 'experiments/battle-terminal-credit-native-recovery-20261023-01'
LAB = Path('/root/heroes3-ai-lab')
RECOVERY01 = LAB / 'evaluations/battle-terminal-credit-recovery-20261023-01'
EXPECTED = {
    'control': '90347e729ae36be8e050fdbcf1cb5973e19ece1fc18374152d2772d0f72e4fb3',
    'candidate': '987d85e50f988267d257c064c856b2da1bb05672c4fce3499720656ea87b1105',
}
sys.path[:0] = [str(TRAIN), str(R), str(LAB / 'src/gym')]
import torch
import restore_learner as restore


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def boundary(path, expected_sha):
    model, opt, bundle, spec = restore.prepare(Path(path), expected_sha)
    counter = restore.install_counter(opt)
    proof = restore.restore_CPU(bundle, spec, model, opt, counter)
    return bundle, counter, proof


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    report = dict(
        schema='terminal-credit-recovery-02-boundary-audit-v1',
        passed=False,
        accepted_for_recovery=False,
        not_an_official_stage_audit=True,
        source_sha256=sha(__file__),
        training_audit_source_sha256=sha(TRAIN / 'audit.py'),
        restore_source_sha256=sha(TRAIN / 'restore_learner.py'),
        new_native_games=0,
        GPU_operations=0,
        optimizer_steps=0,
    )
    try:
        torch.set_num_threads(1)
        control = RECOVERY01 / 'control-phase-2'
        candidate = RECOVERY01 / 'candidate-phase-2'
        checks = {}
        for arm, stage in [('control', control), ('candidate', candidate)]:
            d = read(stage / 'RESULT.json')
            audit = read(stage / 'AUDIT.json')
            assert d['passed'] is True and d['normal_workers_shutdown'] is True
            assert audit['passed'] is True
            assert audit['independent_native_step_and_target_recompute'] is True
            assert audit['source_sha256'] == sha(TRAIN / 'audit.py')
            assert audit['actual_Adam_steps'] == 8448
            assert [r['update'] for r in d['records']] == [65, 66]
            assert all(r['actual_Adam'] == 128 for r in d['records'])
            assert d['records'][-1]['cumulative_Adam'] == 8448
            assert d['admitted_stage_rows'] == d['suffix_stage_rows'] == 3072
            assert d['total_native_stage_rows'] == 6144
            assert len(audit['phase_checks']) == 1
            phase_check = audit['phase_checks'][0]
            assert phase_check['phase'] == 2
            assert phase_check['admitted_observed_rows'] == 1024
            assert phase_check['suffix_observed_rows'] == 1024
            assert phase_check['eligible_workers'] >= 1

            checkpoint = stage / 'update-66.pt'
            checkpoint_sha = sha(checkpoint)
            assert checkpoint_sha == EXPECTED[arm]
            assert d['checkpoint_sha256'] == checkpoint_sha
            assert Path(d['checkpoint']) == checkpoint
            model, opt, bundle, spec = restore.prepare(checkpoint, checkpoint_sha)
            counter = restore.install_counter(opt)
            proof = restore.restore_CPU(bundle, spec, model, opt, counter)
            meta = bundle['terminal_credit_experiment']
            assert bundle['completed_updates'] == 66
            assert bundle['environment_steps'] == 33792
            assert bundle['actual_Adam_steps'] == 8448
            assert counter['steps'] == 8448
            assert bundle['complete_update_boundary'] is True
            assert meta['arm'] == arm and meta['phase'] == 2 and meta['half'] == 1
            assert meta['phase_complete'] is True
            assert meta['parent60_sha256'] == restore.DEFAULT_SHA
            assert meta['admitted_stage_rows'] == 3072
            assert meta['suffix_stage_rows'] == 3072
            assert meta['total_native_stage_rows'] == 6144
            frozen = bundle['frozen_inputs']['input_sha256']
            missing = [path for path in frozen if not Path(path).exists()]
            mismatch = [path for path, expected in frozen.items()
                        if Path(path).exists() and sha(path) != expected]
            assert not missing and not mismatch
            checks[arm] = dict(
                stage=str(stage),
                checkpoint=str(checkpoint),
                checkpoint_sha256=checkpoint_sha,
                stage_result_sha256=sha(stage / 'RESULT.json'),
                stage_audit_sha256=sha(stage / 'AUDIT.json'),
                stage_progress_sha256=sha(stage / 'PROGRESS.json'),
                phase2_audit_passed=True,
                eligible_workers=phase_check['eligible_workers'],
                completed_updates=bundle['completed_updates'],
                environment_steps=bundle['environment_steps'],
                actual_Adam_steps=bundle['actual_Adam_steps'],
                frozen_inputs_checked=len(frozen),
                boundary_restored=True,
            )

        failed = RECOVERY01 / 'control-phase-3'
        failed_result = read(failed / 'RESULT.json')
        assert failed_result['passed'] is False
        assert failed_result['records'] == []
        assert failed_result['error'] == 'AssertionError()'
        assert failed_result['actual_Adam_steps'] == 8448
        assert failed_result['partial_native_not_restorable'] is True
        assert not (failed / 'PROGRESS.json').exists()
        assert not (failed / 'phase-3').exists()
        assert not list(failed.glob('update-*.pt'))
        assert (failed / 'RESTORATION.json').is_file()
        failed_log = RECOVERY01 / 'control-phase-3.log'
        assert failed_log.is_file()
        report.update(
            passed=True,
            accepted_for_recovery=True,
            recovery_01=str(RECOVERY01),
            control=checks['control'],
            candidate=checks['candidate'],
            accepted_boundaries=EXPECTED,
            failed_stage=dict(
                stage=str(failed),
                result_sha256=sha(failed / 'RESULT.json'),
                log_sha256=sha(failed_log),
                restoration_sha256=sha(failed / 'RESTORATION.json'),
                records=[],
                progress_exists=False,
                updates_created=[],
            ),
            acceptance_scope='update-66 starting boundaries only; recovery-01 control-phase-3 remains failed',
        )
    except BaseException as error:
        report.update(passed=False, accepted_for_recovery=False,
                      error=repr(error), traceback=traceback.format_exc())
        raise
    finally:
        (a.out / 'RECOVERY_02_AUDIT.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
