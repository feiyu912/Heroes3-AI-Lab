"""Reviewed recovery controller for the stopped terminal-credit run.

Default is plan-only. --execute owns both leases, accepts the independently
audited control update-64 boundary, runs candidate phase 1 from update-62, then
continues both arms through phases 2..3. It never re-runs control phase 1 and
never reseeds. Optional --evaluate runs the pre-registered 96-game DEV.
"""
import argparse
import fcntl
import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
R = ROOT / 'research'
OLD = ROOT / 'experiments/battle-terminal-credit-native-20261023'
LAB = Path('/root/heroes3-ai-lab')
OLD_RUN = LAB / 'evaluations/battle-terminal-credit-native-20261023-01'
CONTROL64 = OLD_RUN / 'control-phase-1/update-64.pt'
CONTROL63 = OLD_RUN / 'control-phase-1/update-63.pt'
CANDIDATE62 = OLD_RUN / 'candidate-micro/update-62.pt'
OLD_RESULT = OLD_RUN / 'control-phase-1/RESULT.json'
OLD_PROGRESS = OLD_RUN / 'control-phase-1/PROGRESS.json'
OLD_LOG = OLD_RUN / 'control-phase-1.log'
OLD_TARGETS = OLD_RUN / 'control-phase-1/phase-1/TARGETS.pt'
INCIDENT = ROOT / 'experiments/takeover-20261023/incident-01'
INCIDENT_MD = INCIDENT / 'INCIDENT_01_CONTROL_PHASE_1_RESOURCE_GATE.md'
INCIDENT_CHECK = INCIDENT / 'POST_INCIDENT_CHECK.json'

sys.path[:0] = [str(HERE), str(R), str(LAB / 'src/gym')]
import leases
import restore_learner as restore
from lab_io import atomic_json


def inputs():
    spec = importlib.util.spec_from_file_location('_old_freeze', OLD / 'run.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    old.PARENT = LAB / 'evaluations/battle-diverse60-native-02/models/1792504676114060650/update-30.pt'
    old.PARENT_SHA = 'dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa'
    frozen = old.inputs()
    for path in HERE.iterdir():
        if path.is_file():
            frozen[str(path)] = restore.sha(path)
    frozen[str(restore.DEFAULT_CHECKPOINT)] = restore.DEFAULT_SHA
    for path in [CONTROL64, CONTROL63, CANDIDATE62, OLD_RESULT, OLD_PROGRESS,
                 OLD_LOG, OLD_TARGETS, INCIDENT_MD, INCIDENT_CHECK]:
        frozen[str(path)] = restore.sha(path)
    return frozen


def command(out, arm, start, stop, checkpoint, expected_sha, freeze):
    return ['bash', str(R / 'run-lab.sh'), str(HERE / 'train.py'),
            '--checkpoint', str(checkpoint), '--expected-sha', expected_sha,
            '--freeze', str(freeze), '--out', str(out), '--arm', arm,
            '--phase-start', str(start), '--phase-stop', str(stop)]


def entry(checkpoint, sha, actual_adam, admitted, suffix, native):
    return dict(checkpoint=str(checkpoint), checkpoint_sha256=sha,
                actual_Adam_steps=actual_adam, new_Adam_steps=actual_adam - 7680,
                admitted_stage_rows=admitted, suffix_stage_rows=suffix,
                native_stage_rows=native)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--evaluate', action='store_true')
    a = p.parse_args()
    assert restore.sha(restore.DEFAULT_CHECKPOINT) == restore.DEFAULT_SHA
    assert CONTROL64.exists() and CANDIDATE62.exists() and CONTROL63.exists()
    assert all(path.exists() for path in [OLD_RESULT, OLD_PROGRESS, OLD_LOG, OLD_TARGETS,
                                          INCIDENT_MD, INCIDENT_CHECK])
    a.out.mkdir(parents=True, exist_ok=False)
    frozen = dict(schema='terminal-drain-prefix-credit-v1', input_sha256=inputs())
    atomic_json(a.out / 'FREEZE.json', frozen)
    plan = dict(
        schema='terminal-drain-prefix-credit-recovery-v1',
        parent_checkpoint=str(restore.DEFAULT_CHECKPOINT),
        parent_sha256=restore.DEFAULT_SHA,
        parent_Adam=7680,
        control_start_checkpoint=str(CONTROL64),
        control_start_sha256=restore.sha(CONTROL64),
        candidate_start_checkpoint=str(CANDIDATE62),
        candidate_start_sha256=restore.sha(CANDIDATE62),
        accepted_control_boundary_sha256=restore.sha(CONTROL64),
        control_phase_1_official_passed=False,
        control_phase_1_official_audit=False,
        recovery_audit=str(a.out / 'recovery-audit/RECOVERY_AUDIT.json'),
        no_control_phase_1_replay=True,
        no_reseed=True,
        schedule=['candidate-phase-1', 'control-phase-2', 'candidate-phase-2',
                  'control-phase-3', 'candidate-phase-3'],
        global_updates=list(range(61, 69)),
        admitted_per_arm=4096,
        suffix_per_arm=4096,
        native_per_arm=8192,
        planned_Adam_per_arm=1024,
        evaluation=a.evaluate,
        DEV_games=96,
        DEV_seed_base=2026107600,
        execute=a.execute,
        resource_policy=dict(
            prephase_ram_gt_mib=4 * 1024,
            prephase_swap_lt_mib=256,
            postupdate_ram_gt_mib=2 * 1024,
            postupdate_swap='recorded, not a stop condition in this recovery',
            postupdate_swap_lt_mib=None,
        ),
        recovery_reason='control-phase-1 completed updates 63/64 and saved a complete update-64 boundary, then stopped on its post-update resource assertion before recording update 64. The read-only recovery audit validates raw/targets and both boundaries. The post-update swap assertion was stricter than the approved plan and is replaced by logging; the RAM reserve and pre-phase swap guard remain.',
    )
    atomic_json(a.out / 'PLAN.json', plan)
    if not a.execute:
        print(json.dumps(dict(plan_only=True, path=str(a.out / 'PLAN.json'),
                              freeze_entries=len(frozen['input_sha256'])), indent=2))
        return 0
    assert all(os.environ.get(key) in (None, '', '0') for key in
               ['LAB_NATIVE_ONNX_CUDA', 'LAB_ONNX_CUDA', 'LAB_BATTLEAI_TEACHER'])
    env = dict(os.environ, LAB_PYTHON=str(LAB / 'gpu-venv/bin/python'),
               LAB_STAGED_BOOT='1',
               LAB_WORKER_ROOT=str(LAB / 'workers' / (a.out.name + '-bootstrap')),
               CUBLAS_WORKSPACE_CONFIG=':4096:8',
               TERMINAL_CREDIT_LEASE_OWNER='1')
    handles = []
    result = dict(passed=False, qualification=True, arms={}, ability_promotion=False,
                  recovery=dict(control_phase_1_official_passed=False,
                                control_phase_1_official_audit=False,
                                control_start_checkpoint=str(CONTROL64),
                                control_start_sha256=restore.sha(CONTROL64),
                                candidate_start_checkpoint=str(CANDIDATE62),
                                candidate_start_sha256=restore.sha(CANDIDATE62),
                                no_control_phase_1_replay=True,
                                no_reseed=True,
                                resource_policy=plan['resource_policy']))

    def invoke(name, arm, start, stop, checkpoint, checkpoint_sha):
        stage = a.out / name
        assert not stage.exists()
        with (a.out / (name + '.log')).open('w') as stream:
            code = leases.run_owned(
                command(stage, arm, start, stop, checkpoint, checkpoint_sha,
                        a.out / 'FREEZE.json'),
                env=env, stream=stream, pass_fds=[h.fileno() for h in handles])
        assert code == 0, name + ' failed: preserve evidence, no retry'
        d = json.loads((stage / 'RESULT.json').read_text())
        assert d['passed'] and d['normal_workers_shutdown']
        expected_updates = list(range(61 + start * 2, 61 + stop * 2))
        assert [record['update'] for record in d['records']] == expected_updates
        assert all(record['actual_Adam'] == 128 for record in d['records'])
        assert d['actual_Adam_steps'] == 7680 + 256 * stop
        assert d['admitted_stage_rows'] == d['suffix_stage_rows'] == 1024 * stop
        assert d['total_native_stage_rows'] == 2048 * stop
        with (a.out / (name + '-audit.log')).open('w') as stream:
            audit_code = leases.run_owned(
                [str(LAB / 'venv/bin/python'), str(HERE / 'audit.py'),
                 '--stage', str(stage)],
                env=env, stream=stream, pass_fds=[h.fileno() for h in handles])
        assert audit_code == 0, name + ' independent raw/target audit failed'
        audit = json.loads((stage / 'AUDIT.json').read_text())
        assert audit['passed']
        return d

    try:
        for name in ['.gpu-learner-lock', '.pool-lock']:
            handle = (LAB / 'evaluations' / name).open('a')
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            handles.append(handle)
        env['TERMINAL_CREDIT_LEASES'] = json.dumps(
            [leases.metadata(h, path) for h, path in zip(handles, leases.PATHS)])

        audit_out = a.out / 'recovery-audit'
        audit_out.mkdir()
        with (a.out / 'recovery-audit.log').open('w') as stream:
            audit_code = leases.run_owned(
                [str(LAB / 'venv/bin/python'), str(HERE / 'recovery_audit.py'),
                 '--stage', str(OLD_RUN / 'control-phase-1'), '--out', str(audit_out)],
                env=env, stream=stream, pass_fds=[h.fileno() for h in handles])
        assert audit_code == 0, 'recovery audit rejected the control update-64 boundary'
        recovery_audit = json.loads((audit_out / 'RECOVERY_AUDIT.json').read_text())
        assert recovery_audit['passed'] and recovery_audit['accepted_for_recovery']
        result['recovery']['audit'] = recovery_audit
        result['arms']['control'] = entry(CONTROL64, restore.sha(CONTROL64),
                                          8192, 2048, 2048, 4096)
        atomic_json(a.out / 'RESULT.partial.json', result)

        d = invoke('candidate-phase-1', 'candidate', 1, 2, CANDIDATE62,
                   restore.sha(CANDIDATE62))
        result['arms']['candidate'] = entry(d['checkpoint'], d['checkpoint_sha256'],
                                            d['actual_Adam_steps'], d['admitted_stage_rows'],
                                            d['suffix_stage_rows'], d['total_native_stage_rows'])
        atomic_json(a.out / 'RESULT.partial.json', result)
        assert result['arms']['control']['actual_Adam_steps'] == result['arms']['candidate']['actual_Adam_steps'] == 8192

        for phase in [2, 3]:
            for arm in ['control', 'candidate']:
                previous = result['arms'][arm]
                d = invoke(arm + '-phase-' + str(phase), arm, phase, phase + 1,
                           Path(previous['checkpoint']), previous['checkpoint_sha256'])
                result['arms'][arm] = entry(d['checkpoint'], d['checkpoint_sha256'],
                                            d['actual_Adam_steps'], d['admitted_stage_rows'],
                                            d['suffix_stage_rows'], d['total_native_stage_rows'])
                atomic_json(a.out / 'RESULT.partial.json', result)
            assert result['arms']['control']['actual_Adam_steps'] == result['arms']['candidate']['actual_Adam_steps'] == 7680 + 256 * (phase + 1)

        for h in reversed(handles):
            h.close()
        handles = []
        env.pop('TERMINAL_CREDIT_LEASES', None)
        env.pop('TERMINAL_CREDIT_LEASE_OWNER', None)
        leases.finish_owned_groups()

        if a.evaluate:
            with (a.out / 'DEV-controller.log').open('w') as stream:
                code = leases.run_owned(
                    [str(LAB / 'venv/bin/python'), str(HERE / 'evaluate.py'),
                     '--run', str(a.out)],
                    env=env, stream=stream)
            assert code == 0, 'DEV invalid, no retrain'
            result['DEV'] = json.loads((a.out / 'DEV-RESULT.json').read_text())['DEV']
        result['passed'] = True
    except BaseException as error:
        result['error'] = repr(error)
    finally:
        leases.finish_owned_groups()
        for h in reversed(handles):
            h.close()
        atomic_json(a.out / 'RESULT.json', result)
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
