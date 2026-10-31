"""Recovery-02: continue from validated update-66 boundaries after a swap stop.

The frozen recovery-01 training package is reused unchanged. This controller
only adds an external, bounded pre-stage wait that records every resource
sample and starts a stage after the original thresholds pass. It never re-runs
phases 1/2 and never reseeds.
"""
import argparse
import fcntl
import json
import os
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
R = ROOT / 'research'
TRAIN = ROOT / 'experiments/battle-terminal-credit-native-recovery-20261023-01'
LAB = Path('/root/heroes3-ai-lab')
RECOVERY01 = LAB / 'evaluations/battle-terminal-credit-recovery-20261023-01'
RECOVERY01_FREEZE = RECOVERY01 / 'FREEZE.json'
CONTROL66 = RECOVERY01 / 'control-phase-2/update-66.pt'
CANDIDATE66 = RECOVERY01 / 'candidate-phase-2/update-66.pt'
FAILED = RECOVERY01 / 'control-phase-3'
INCIDENT = ROOT / 'experiments/takeover-20261023/incident-02/INCIDENT_02_CONTROL_PHASE_3_PREPHASE_RESOURCE_GATE.md'

sys.path[:0] = [str(TRAIN), str(R), str(LAB / 'src/gym')]
import leases
import restore_learner as restore
from lab_io import atomic_json


def sha(path):
    return restore.sha(path)


def stage_files(stage):
    return [stage / 'RESULT.json', stage / 'AUDIT.json', stage / 'PROGRESS.json',
            stage / 'RESTORATION.json', stage / 'phase-2/TARGETS.pt',
            stage / 'phase-2/WORKERS.json']


def inputs():
    frozen = json.loads(RECOVERY01_FREEZE.read_text())['input_sha256']
    for path in HERE.iterdir():
        if path.is_file():
            frozen[str(path)] = sha(path)
    extra = [CONTROL66, CANDIDATE66, RECOVERY01_FREEZE,
             RECOVERY01 / 'RESULT.json', RECOVERY01 / 'RESULT.partial.json',
             FAILED / 'RESULT.json', FAILED / 'RESTORATION.json',
             RECOVERY01 / 'control-phase-3.log', INCIDENT]
    extra += stage_files(RECOVERY01 / 'control-phase-2')
    extra += stage_files(RECOVERY01 / 'candidate-phase-2')
    for path in extra:
        assert path.exists(), path
        frozen[str(path)] = sha(path)
    return frozen


def snapshot():
    m = {k: int(v.split()[0]) for k, v in
         (line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())}
    disk = shutil.disk_usage(LAB)
    return dict(available_mib=m['MemAvailable'] / 1024,
                swap_used_mib=(m['SwapTotal'] - m['SwapFree']) / 1024,
                disk_free_gib=disk.free / 1024 ** 3)


def command(out, arm, checkpoint, expected_sha, freeze):
    return ['bash', str(R / 'run-lab.sh'), str(TRAIN / 'train.py'),
            '--checkpoint', str(checkpoint), '--expected-sha', expected_sha,
            '--freeze', str(freeze), '--out', str(out), '--arm', arm,
            '--phase-start', '3', '--phase-stop', '4']


def entry(checkpoint, checkpoint_sha):
    return dict(checkpoint=str(checkpoint), checkpoint_sha256=checkpoint_sha,
                actual_Adam_steps=8448, new_Adam_steps=768,
                admitted_stage_rows=3072, suffix_stage_rows=3072,
                native_stage_rows=6144)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--evaluate', action='store_true')
    a = p.parse_args()
    assert CONTROL66.exists() and CANDIDATE66.exists()
    assert FAILED.exists() and INCIDENT.exists()
    a.out.mkdir(parents=True, exist_ok=False)
    frozen = dict(schema='terminal-drain-prefix-credit-v1', input_sha256=inputs())
    atomic_json(a.out / 'FREEZE.json', frozen)
    plan = dict(
        schema='terminal-drain-prefix-credit-recovery-02-v1',
        parent_checkpoint=str(restore.DEFAULT_CHECKPOINT),
        parent_sha256=restore.DEFAULT_SHA,
        parent_Adam=7680,
        recovery_from='recovery-01 update-66 phase-2 boundaries',
        control_start_checkpoint=str(CONTROL66),
        control_start_sha256=sha(CONTROL66),
        candidate_start_checkpoint=str(CANDIDATE66),
        candidate_start_sha256=sha(CANDIDATE66),
        failed_stage=str(FAILED),
        failed_stage_replayed=False,
        phase1_replayed=False,
        phase2_replayed=False,
        no_reseed=True,
        schedule=['control-phase-3', 'candidate-phase-3'],
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
            prephase_ram_gt_mib=4096,
            prephase_swap_lt_mib=256,
            prephase_wait_seconds=180,
            prephase_poll_seconds=5,
            postupdate_ram_gt_mib=2048,
            postupdate_swap='recorded, not a stop condition',
            thresholds_changed=False,
        ),
        recovery_reason='recovery-01 control-phase-3 stopped before any update on the pre-phase resource assertion; candidate-phase-2 had ended at swap 309.3 MiB and the pre-phase threshold is 256 MiB. Recovery-02 waits for the same threshold to be met, logs values, then runs phase 3 from the audited update-66 boundaries.',
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
    result = dict(
        passed=False, qualification=True,
        arms=dict(control=entry(CONTROL66, sha(CONTROL66)),
                  candidate=entry(CANDIDATE66, sha(CANDIDATE66))),
        ability_promotion=False,
        recovery=dict(
            recovery_01=str(RECOVERY01),
            failed_stage=str(FAILED),
            control_start_checkpoint=str(CONTROL66),
            control_start_sha256=sha(CONTROL66),
            candidate_start_checkpoint=str(CANDIDATE66),
            candidate_start_sha256=sha(CANDIDATE66),
            phase1_replayed=False,
            phase2_replayed=False,
            no_reseed=True,
            resource_policy=plan['resource_policy'],
        ),
    )

    def wait_for_stage(name, limit=180):
        start = time.monotonic()
        initial = snapshot()
        samples = [dict(elapsed_s=0.0, **initial)]
        while initial['swap_used_mib'] >= 256 and time.monotonic() - start < limit:
            time.sleep(5)
            samples.append(dict(elapsed_s=time.monotonic() - start, **snapshot()))
            if samples[-1]['swap_used_mib'] < 256:
                break
        final = snapshot()
        record = dict(stage=name, initial=initial, final=final,
                      samples=samples, wait_seconds=time.monotonic() - start,
                      thresholds=dict(available_mib_gt=4096, swap_used_mib_lt=256,
                                      disk_free_gib_gt=10))
        atomic_json(a.out / ('WAIT-' + name + '.json'), record)
        assert (final['available_mib'] > 4096 and final['swap_used_mib'] < 256
                and final['disk_free_gib'] > 10), f'Pre-stage readiness failed: {record}'
        return record

    def invoke(name, arm, checkpoint, checkpoint_sha):
        wait_for_stage(name)
        stage = a.out / name
        assert not stage.exists()
        with (a.out / (name + '.log')).open('w') as stream:
            code = leases.run_owned(
                command(stage, arm, checkpoint, checkpoint_sha, a.out / 'FREEZE.json'),
                env=env, stream=stream, pass_fds=[h.fileno() for h in handles])
        assert code == 0, name + ' failed: preserve evidence, no retry'
        d = json.loads((stage / 'RESULT.json').read_text())
        assert d['passed'] and d['normal_workers_shutdown']
        assert [record['update'] for record in d['records']] == [67, 68]
        assert all(record['actual_Adam'] == 128 for record in d['records'])
        assert d['actual_Adam_steps'] == 8704
        assert d['admitted_stage_rows'] == d['suffix_stage_rows'] == 4096
        assert d['total_native_stage_rows'] == 8192
        with (a.out / (name + '-audit.log')).open('w') as stream:
            audit_code = leases.run_owned(
                [str(LAB / 'venv/bin/python'), str(TRAIN / 'audit.py'),
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
                [str(LAB / 'venv/bin/python'), str(HERE / 'boundary_audit_02.py'),
                 '--out', str(audit_out)],
                env=env, stream=stream, pass_fds=[h.fileno() for h in handles])
        assert audit_code == 0, 'recovery-02 boundary audit rejected update-66'
        boundary_audit = json.loads((audit_out / 'RECOVERY_02_AUDIT.json').read_text())
        assert boundary_audit['passed'] and boundary_audit['accepted_for_recovery']
        result['recovery']['audit'] = boundary_audit
        atomic_json(a.out / 'RESULT.partial.json', result)

        d = invoke('control-phase-3', 'control', CONTROL66, sha(CONTROL66))
        result['arms']['control'] = dict(
            checkpoint=d['checkpoint'], checkpoint_sha256=d['checkpoint_sha256'],
            actual_Adam_steps=d['actual_Adam_steps'],
            new_Adam_steps=d['actual_Adam_steps'] - 7680,
            admitted_stage_rows=d['admitted_stage_rows'],
            suffix_stage_rows=d['suffix_stage_rows'],
            native_stage_rows=d['total_native_stage_rows'])
        atomic_json(a.out / 'RESULT.partial.json', result)

        d = invoke('candidate-phase-3', 'candidate', CANDIDATE66, sha(CANDIDATE66))
        result['arms']['candidate'] = dict(
            checkpoint=d['checkpoint'], checkpoint_sha256=d['checkpoint_sha256'],
            actual_Adam_steps=d['actual_Adam_steps'],
            new_Adam_steps=d['actual_Adam_steps'] - 7680,
            admitted_stage_rows=d['admitted_stage_rows'],
            suffix_stage_rows=d['suffix_stage_rows'],
            native_stage_rows=d['total_native_stage_rows'])
        atomic_json(a.out / 'RESULT.partial.json', result)
        assert (result['arms']['control']['actual_Adam_steps']
                == result['arms']['candidate']['actual_Adam_steps'] == 8704)

        for h in reversed(handles):
            h.close()
        handles = []
        env.pop('TERMINAL_CREDIT_LEASES', None)
        env.pop('TERMINAL_CREDIT_LEASE_OWNER', None)
        leases.finish_owned_groups()

        if a.evaluate:
            with (a.out / 'DEV-controller.log').open('w') as stream:
                code = leases.run_owned(
                    [str(LAB / 'venv/bin/python'), str(TRAIN / 'evaluate.py'),
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
