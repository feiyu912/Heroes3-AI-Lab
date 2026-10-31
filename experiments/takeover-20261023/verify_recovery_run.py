"""Read-only post-run verification for the terminal-credit recovery."""
import hashlib
import json
import sys
from pathlib import Path

RUN = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-01')
OLD = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-native-20261023-01')
NEW = Path('/mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-recovery-20261023-01')
sys.path[:0] = [str(NEW), '/mnt/g/Heroes3-AI-Lab/research', '/root/heroes3-ai-lab/src/gym']
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
    return dict(sha256=expected_sha, completed_updates=bundle['completed_updates'],
                environment_steps=bundle['environment_steps'],
                actual_Adam_steps=bundle['actual_Adam_steps'],
                proof=proof)


result = read(RUN / 'RESULT.json')
assert result['passed'] is True, result
assert set(result['arms']) == {'control', 'candidate'}
assert result['arms']['control']['actual_Adam_steps'] == 8704
assert result['arms']['candidate']['actual_Adam_steps'] == 8704
assert len(result['DEV']) == 6
assert read(RUN / 'recovery-audit/RECOVERY_AUDIT.json')['accepted_for_recovery'] is True
assert read(RUN / 'DEV-RESULT.json')['passed'] is True
assert read(RUN / 'DEV-RAW-AUDIT.json')['passed'] is True
assert read(RUN / 'DEV-NN-REPLAY/AUDIT.json')['passed'] is True

freeze = read(RUN / 'FREEZE.json')['input_sha256']
assert all(sha(p) == h for p, h in freeze.items())
assert len(freeze) >= 553

stages = {
    'candidate-phase-1': ([63, 64], 8192),
    'control-phase-2': ([65, 66], 8448),
    'candidate-phase-2': ([65, 66], 8448),
    'control-phase-3': ([67, 68], 8704),
    'candidate-phase-3': ([67, 68], 8704),
}
stage_summary = {}
for name, (expected_updates, expected_adam) in stages.items():
    stage = RUN / name
    d = read(stage / 'RESULT.json')
    a = read(stage / 'AUDIT.json')
    assert d['passed'] and d['normal_workers_shutdown']
    assert a['passed']
    assert [r['update'] for r in d['records']] == expected_updates
    assert all(r['actual_Adam'] == 128 for r in d['records'])
    assert d['actual_Adam_steps'] == expected_adam
    phase_count = (expected_updates[-1] - 60) // 2
    assert d['admitted_stage_rows'] == d['suffix_stage_rows'] == 1024 * phase_count
    assert d['total_native_stage_rows'] == 2048 * phase_count
    stage_summary[name] = dict(actual_Adam_steps=d['actual_Adam_steps'],
                               checkpoint=d['checkpoint'],
                               checkpoint_sha256=d['checkpoint_sha256'],
                               audit_passed=a['passed'])

assert read(RUN / 'candidate-phase-1/AUDIT.json')['actual_Adam_steps'] == 8192
assert read(RUN / 'control-phase-3/AUDIT.json')['actual_Adam_steps'] == 8704

control = check_checkpoint(result['arms']['control']['checkpoint'],
                           result['arms']['control']['checkpoint_sha256'], 'control')
candidate = check_checkpoint(result['arms']['candidate']['checkpoint'],
                             result['arms']['candidate']['checkpoint_sha256'], 'candidate')

# The old failed stage must remain exactly failed and must not have gained an audit.
old_result = read(OLD / 'control-phase-1/RESULT.json')
assert old_result['passed'] is False and old_result['error'] == 'AssertionError()'
assert not (OLD / 'control-phase-1/AUDIT.json').exists()
assert sha(OLD / 'control-phase-1/update-64.pt') == '4ef6e7e27ffcc56f7b261a55c52e38505be24a162f8196d2ccd3a60be734cb59'

wp = RUN / 'RESULT.partial.json'
assert wp.exists()
partial = read(wp)
assert set(partial['arms']) == {'control', 'candidate'}

# Descriptive small-sample summaries only; no population or promotion claim.
dev = result['DEV']
summary = {}
for item in dev:
    d = read(item['report'])
    assert len(d['battles']) == 16
    summary[item['model'] + '/' + item['opponent']] = d['summary'][0]
pairs = read(RUN / 'DEV-RAW-AUDIT.json')['DEV']['pairs']
control_vs_candidate = read(RUN / 'DEV-RAW-AUDIT.json')['DEV']['control_vs_candidate_pairs']
net = sum(p['win_delta'] for p in control_vs_candidate)

print(json.dumps(dict(
    run=str(RUN),
    passed=result['passed'],
    arms=result['arms'],
    stages=stage_summary,
    recovery_audit=read(RUN / 'recovery-audit/RECOVERY_AUDIT.json')['accepted_boundary_sha256'],
    old_failed_stage_preserved=True,
    freeze_entries=len(freeze),
    dev=summary,
    dev_unique_games=read(RUN / 'DEV-RAW-AUDIT.json')['DEV']['unique_games'],
    control_vs_candidate_net_win_delta=net,
    control_vs_candidate_pairs=len(control_vs_candidate),
    final_checkpoints=dict(control=control, candidate=candidate),
), indent=2))
