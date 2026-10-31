"""Read-only comparison of the two actual native-training restoration records."""
import argparse
import hashlib
import json
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--run', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
paths = {arm: a.run / arm / 'training.restoration.json' for arm in ('control', 'candidate')}
records = {arm: json.loads(path.read_text()) for arm, path in paths.items()}
for key in ('model_digest', 'Adam_digest_before_lr_override', 'parent_checkpoint_sha256',
            'parent_completed_updates', 'parent_environment_steps', 'parent_actual_Adam_steps',
            'schedule_epoch', 'actual_Adam_counter_before_first_sampling'):
    assert records['control'][key] == records['candidate'][key], key
for arm, r in records.items():
    assert r['CUDA_restore_executed'] and r['model_CPU_to_CUDA_exact'] and r['Adam_CPU_to_CUDA_exact']
    assert r['actual_Adam_counter_before_first_sampling'] == 3840
    assert r['native_environment_restored'] is False
    assert all(r['all_RNG_before_first_sampling'][key] is True for key in
               ('Torch_CPU_exact', 'Torch_CUDA_exact', 'Python_exact', 'NumPy_exact'))
    assert r['lr_override'] == dict(arm=arm, group='last_graph', before=1e-6,
        after=1e-6 if arm == 'control' else 3e-6, heads_unchanged=1e-5)
result = dict(passed=True, actual_restoration_records=True,
    model_and_pre_override_Adam_digests_equal=True, four_RNG_restoration_records_exact=True,
    inherited_counter=3840, native_environment_restored=False, audit_optimizer_steps=0,
    input_sha256={str(path): sha(path) for path in paths.values()},
    limitation='Checks actual saved restoration records and their identities; does not certify later training or identical native hidden state.')
a.out.mkdir(parents=True, exist_ok=False)
(a.out / 'AUDIT.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
