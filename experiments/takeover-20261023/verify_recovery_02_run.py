"""Read-only post-run verification for terminal-credit recovery-02."""
import hashlib
import json
import sys
from pathlib import Path

RUN = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-02')
RECOVERY01 = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-01')
NATIVE = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-native-20261023-01')
NEW = Path('/mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-recovery-20261023-02')
TRAIN = Path('/mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-recovery-20261023-01')
sys.path[:0] = [str(TRAIN), '/mnt/g/Heroes3-AI-Lab/research', '/root/heroes3-ai-lab/src/gym']
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


def check_checkpoint(path, expected_sha, arm):
    model, opt, bundle, spec = restore.prepare(Path(path), expected_sha)
    counter = restore.install_counter(opt)
    proof = restore.restore_CPU(bundle, spec, model, opt, counter)
    meta = bundle['terminal_credit_experiment']
    assert bundle['completed_updates'] == 68
    assert bundle['environment_steps'] == 34816
    assert bundle['actual_Adam_steps'] == 8704
    assert bundle['complete_update_boundary'] is True
    assert meta['arm'] == arm and meta['phase'] == 3 and meta['phase_complete'] is True
    assert meta['parent60_sha256'] == restore.DEFAULT_SHA
    assert meta['admitted_stage_rows'] == 4096
    assert meta['suffix_stage_rows'] == 4096
    assert meta['total_native_stage_rows'] == 8192
    return dict(sha256=expected_sha, completed_updates=bundle['completed_updates'],
                environment_steps=bundle['environment_steps'],
                actual_Adam_steps=bundle['actual_Adam_steps'], boundary_restored=True)


result = read(RUN / 'RESULT.json')
assert result['passed'] is True, result
assert set(result['arms']) == {'control', 'candidate'}
assert result['arms']['control']['actual_Adam_steps'] == 8704
assert result['arms']['candidate']['actual_Adam_steps'] == 8704
assert len(result['DEV']) == 6
audit02 = read(RUN / 'recovery-audit/RECOVERY_02_AUDIT.json')
assert audit02['passed'] is True and audit02['accepted_for_recovery'] is True
assert read(RUN / 'DEV-RESULT.json')['passed'] is True
assert read(RUN / 'DEV-RAW-AUDIT.json')['passed'] is True
assert read(RUN / 'DEV-NN-REPLAY/AUDIT.json')['passed'] is True

freeze = read(RUN / 'FREEZE.json')['input_sha256']
assert all(sha(p) == h for p, h in freeze.items())
assert len(freeze) >= 578

stage_summary = {}
for name, arm in [('control-phase-3', 'control'), ('candidate-phase-3', 'candidate')]:
    stage = RUN / name
    d = read(stage / 'RESULT.json')
    a = read(stage / 'AUDIT.json')
    assert d['passed'] is True and d['normal_workers_shutdown'] is True
    assert a['passed'] is True
    assert [r['update'] for r in d['records']] == [67, 68]
    assert all(r['actual_Adam'] == 128 for r in d['records'])
    assert d['actual_Adam_steps'] == 8704
    assert d['admitted_stage_rows'] == d['suffix_stage_rows'] == 4096
    assert d['total_native_stage_rows'] == 8192
    wait = read(RUN / ('WAIT-' + name + '.json'))
    assert wait['final']['swap_used_mib'] < 256
    assert wait['final']['available_mib'] > 4096
    assert wait['final']['disk_free_gib'] > 10
    stage_summary[name] = dict(actual_Adam_steps=d['actual_Adam_steps'],
                               checkpoint=d['checkpoint'],
                               checkpoint_sha256=d['checkpoint_sha256'],
                               audit_passed=a['passed'],
                               wait_seconds=wait['wait_seconds'],
                               initial_swap=wait['initial']['swap_used_mib'],
                               final_swap=wait['final']['swap_used_mib'])

control = check_checkpoint(result['arms']['control']['checkpoint'],
                           result['arms']['control']['checkpoint_sha256'], 'control')
candidate = check_checkpoint(result['arms']['candidate']['checkpoint'],
                             result['arms']['candidate']['checkpoint_sha256'], 'candidate')

# Recovery-01 failure and completed boundaries must remain preserved.
failed = read(RECOVERY01 / 'control-phase-3/RESULT.json')
assert failed['passed'] is False and failed['records'] == []
assert failed['error'] == 'AssertionError()'
assert not (RECOVERY01 / 'control-phase-3/PROGRESS.json').exists()
assert not list((RECOVERY01 / 'control-phase-3').glob('update-*.pt'))
assert read(RECOVERY01 / 'RESULT.json')['arms']['control']['actual_Adam_steps'] == 8448
assert read(RECOVERY01 / 'RESULT.json')['arms']['candidate']['actual_Adam_steps'] == 8448
assert sha(RECOVERY01 / 'control-phase-2/update-66.pt') == '90347e729ae36be8e050fdbcf1cb5973e19ece1fc18374152d2772d0f72e4fb3'
assert sha(RECOVERY01 / 'candidate-phase-2/update-66.pt') == '987d85e50f988267d257c064c856b2da1bb05672c4fce3499720656ea87b1105'
assert sha(NATIVE / 'control-phase-1/update-64.pt') == '4ef6e7e27ffcc56f7b261a55c52e38505be24a162f8196d2ccd3a60be734cb59'

partial = read(RUN / 'RESULT.partial.json')
assert set(partial['arms']) == {'control', 'candidate'}
assert partial['arms']['control']['actual_Adam_steps'] == 8704
assert partial['arms']['candidate']['actual_Adam_steps'] == 8704

# Descriptive small-sample summaries only.
summary = {}
for item in result['DEV']:
    d = read(item['report'])
    assert len(d['battles']) == 16
    summary[item['model'] + '/' + item['opponent']] = d['summary'][0]
raw_audit = read(RUN / 'DEV-RAW-AUDIT.json')['DEV']
net = sum(p['win_delta'] for p in raw_audit['control_vs_candidate_pairs'])

print(json.dumps(dict(
    run=str(RUN),
    passed=result['passed'],
    arms=result['arms'],
    stages=stage_summary,
    recovery02_audit=audit02['accepted_boundaries'],
    old_failure_preserved=True,
    freeze_entries=len(freeze),
    dev=summary,
    dev_unique_games=raw_audit['unique_games'],
    control_vs_candidate_net_win_delta=net,
    control_vs_candidate_pairs=len(raw_audit['control_vs_candidate_pairs']),
    final_checkpoints=dict(control=control, candidate=candidate),
), indent=2))
