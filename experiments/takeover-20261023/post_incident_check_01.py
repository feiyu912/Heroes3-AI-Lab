"""Read-only post-incident validation of the failed control-phase-1 boundary.

This does not run audit.py (which would write AUDIT.json), does not write into
the evaluation stage, does not use CUDA, native workers, or an optimizer.
It recomputes raw target evidence and checks both saved learner boundaries.
Its output is not a stage acceptance and does not authorize resumption.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

RUN = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-native-20261023-01')
HERE = Path('/mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023')
RESEARCH = Path('/mnt/g/Heroes3-AI-Lab/research')
GYM = Path('/root/heroes3-ai-lab/src/gym')
sys.path[:0] = [str(HERE), str(RESEARCH), str(GYM)]

import numpy as np
import torch

import audit
import restore_learner as restore
import targets

OUT = Path('/mnt/g/Heroes3-AI-Lab/experiments/takeover-20261023/incident-01')
OUT.mkdir(parents=True, exist_ok=True)


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
    return {
        'path': str(path),
        'sha256': expected_sha,
        'completed_updates': bundle['completed_updates'],
        'environment_steps': bundle['environment_steps'],
        'actual_Adam_steps': bundle['actual_Adam_steps'],
        'terminal_credit_experiment': bundle['terminal_credit_experiment'],
        'restore_proof': proof,
    }


torch.set_num_threads(1)
stage = RUN / 'control-phase-1'
result = json.loads((stage / 'RESULT.json').read_text())
progress = json.loads((stage / 'PROGRESS.json').read_text())
assert result['arm'] == 'control'
assert [r['update'] for r in result['records']] == [63]
assert [r['update'] for r in progress['records']] == [63]
assert not (stage / 'AUDIT.json').exists()

folder = stage / 'phase-1'
p0, next0, c0, f0 = audit.raw_check(folder / 'admitted-0.pt', 32, True)
p1, next1, c1, f1 = audit.raw_check(folder / 'admitted-1.pt', 32, True, next0)
suffix, nexts, cs, fs = audit.raw_check(folder / 'suffix.pt', 64, False, next1)
assert p1['behavior_checkpoint_sha256'] == suffix['behavior_checkpoint_sha256']

saved = audit.payload(folder / 'TARGETS.pt')
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

record63 = result['records'][0]
assert Path(suffix['behavior_checkpoint']) == Path(record63['checkpoint'])
assert suffix['behavior_checkpoint_sha256'] == record63['checkpoint_sha256']
behavior = torch.load(suffix['behavior_checkpoint'], map_location='cpu', weights_only=True)
assert restore.digest(restore.weight_state(behavior)) == saved['behavior_model_digest'] == saved['behavior_model_after_suffix']
assert restore.digest(behavior['optimizer_state_dict']) == saved['Adam_digest'] == saved['Adam_after_suffix']

boundary63 = boundary(record63['checkpoint'], record63['checkpoint_sha256'])
assert boundary63['completed_updates'] == 63
assert boundary63['environment_steps'] == 32256
assert boundary63['actual_Adam_steps'] == 8064
assert boundary63['terminal_credit_experiment']['phase_complete'] is False

cp64 = stage / 'update-64.pt'
sha64 = sha(cp64)
boundary64 = boundary(cp64, sha64)
assert boundary64['completed_updates'] == 64
assert boundary64['environment_steps'] == 32768
assert boundary64['actual_Adam_steps'] == 8192
meta64 = boundary64['terminal_credit_experiment']
assert meta64['arm'] == 'control' and meta64['phase'] == 1 and meta64['half'] == 1
assert meta64['phase_complete'] is True
assert meta64['parent60_sha256'] == restore.DEFAULT_SHA
assert meta64['admitted_stage_rows'] == 2048
assert meta64['suffix_stage_rows'] == 2048
assert meta64['total_native_stage_rows'] == 4096
assert meta64['target_evidence']['sha256'] == sha(folder / 'TARGETS.pt')
assert meta64['prefix_rollout']['sha256'] == sha(folder / 'admitted-1.pt')

bundle64 = torch.load(cp64, map_location='cpu', weights_only=True)
frozen = bundle64['frozen_inputs']['input_sha256']
frozen_missing = [p for p in frozen if not Path(p).exists()]
frozen_mismatch = [p for p, h in frozen.items() if Path(p).exists() and sha(p) != h]
assert not frozen_missing and not frozen_mismatch

report = {
    'schema': 'post-incident-read-only-check-v1',
    'stage': str(stage),
    'not_a_stage_acceptance': True,
    'resumption_authorized': False,
    'stage_result_passed': result['passed'],
    'stage_result_error': result['error'],
    'official_audit_exists': False,
    'recorded_updates': [r['update'] for r in result['records']],
    'update_64_checkpoint_sha256': sha64,
    'update_64_checkpoint_bytes': cp64.stat().st_size,
    'raw_and_target_recompute_passed': True,
    'boundary_63_restore_passed': True,
    'boundary_64_restore_passed': True,
    'update_64_is_complete_update_boundary': True,
    'update_64_phase_complete': True,
    'update_64_actual_Adam_steps': 8192,
    'update_64_environment_steps': 32768,
    'targets_sha256': sha(folder / 'TARGETS.pt'),
    'raw': {
        'prefix_terminations': c0['terminals'] + c1['terminals'],
        'suffix_terminations': cs['terminals'],
        'prefix_rows': c0['rows'] + c1['rows'],
        'suffix_rows': cs['rows'],
        'journal_files': len(f0 + f1 + fs),
    },
    'eligible_workers': int(np.sum(recomputed['eligible'])),
    'reasons': list(recomputed['reason']),
    'frozen_inputs_checked': len(frozen),
    'frozen_inputs_missing': frozen_missing,
    'frozen_inputs_mismatch': frozen_mismatch,
    'boundary_63': {k: boundary63[k] for k in ['path', 'sha256', 'completed_updates',
                                               'environment_steps', 'actual_Adam_steps']},
    'boundary_64': {k: boundary64[k] for k in ['path', 'sha256', 'completed_updates',
                                               'environment_steps', 'actual_Adam_steps']},
}
path = OUT / 'POST_INCIDENT_CHECK.json'
path.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
