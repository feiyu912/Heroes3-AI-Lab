"""Read-only post-incident diagnostics for the terminal-credit native run.

Does not load models onto CUDA, does not run native workers, does not modify
the evaluation directory. Only reads JSON/checkpoints and process/lock state.
"""
import fcntl
import hashlib
import json
import os
import subprocess
from pathlib import Path

import torch

RUN = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-native-20261023-01')
LAB = Path('/root/heroes3-ai-lab')
LOCK_PATHS = [LAB / 'evaluations/.gpu-learner-lock', LAB / 'evaluations/.pool-lock']


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def meminfo():
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, rest = line.split(':', 1)
        values[key] = int(rest.split()[0])
    return {
        'MemAvailable_mib': values['MemAvailable'] / 1024,
        'SwapTotal_mib': values['SwapTotal'] / 1024,
        'SwapFree_mib': values['SwapFree'] / 1024,
        'SwapUsed_mib': (values['SwapTotal'] - values['SwapFree']) / 1024,
    }


def lock_state():
    result = {}
    for path in LOCK_PATHS:
        try:
            handle = open(path, 'a')
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(handle, fcntl.LOCK_UN)
                result[str(path)] = 'free (lock acquired and released)'
            finally:
                handle.close()
        except BlockingIOError:
            result[str(path)] = 'held by another process'
        except Exception as error:
            result[str(path)] = f'error: {error!r}'
    return result


def processes():
    rows = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmd = (entry / 'cmdline').read_bytes().replace(b'\0', b' ').decode('utf-8', 'replace').strip()
        except Exception:
            continue
        if any(token in cmd for token in ('train.py', 'run.py', 'audit.py', 'vcmiclient', 'VCMI')):
            rows.append((int(entry.name), cmd[:300]))
    return rows


def json_summary(path, keys):
    if not path.exists():
        return {'exists': False}
    d = json.loads(path.read_text())
    return {k: d.get(k) for k in keys}


def stage_summary(name, keys):
    stage = RUN / name
    out = {
        'RESULT': json_summary(stage / 'RESULT.json', keys),
        'AUDIT': json_summary(stage / 'AUDIT.json', [
            'passed', 'stage', 'phase_checks', 'actual_Adam_steps',
            'new_native_stage_rows', 'source_sha256', 'targets_sha256',
            'error']),
    }
    if stage.exists():
        files = [p for p in stage.rglob('*') if p.is_file()]
        out['files'] = len(files)
        out['bytes'] = sum(p.stat().st_size for p in files)
        out['update_checkpoints'] = {
            p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)}
            for p in sorted(stage.glob('update-*.pt'))
        }
        out['raw_counts'] = {
            'decision': len(list(stage.rglob('*-decision.pt'))),
            'return': len(list(stage.rglob('*-return.pt'))),
            'evidence': len(list(stage.rglob('admitted-*.pt'))) + len(list(stage.rglob('suffix.pt'))),
            'targets': len(list(stage.rglob('TARGETS.pt'))),
        }
    return out


def checkpoint_summary(path):
    d = torch.load(path, map_location='cpu', weights_only=False)
    keys = sorted(d.keys())
    selected = {
        'completed_updates': d.get('completed_updates'),
        'environment_steps': d.get('environment_steps'),
        'actual_Adam_steps': d.get('actual_Adam_steps'),
        'complete_update_boundary': d.get('complete_update_boundary'),
        'native_environment_restorable': d.get('native_environment_restorable'),
        'terminal_credit_experiment': d.get('terminal_credit_experiment'),
    }
    return {'top_level_keys': keys, 'selected': selected}


print('== MEMINFO ==')
print(json.dumps(meminfo(), indent=2))
print('== LOCKS ==')
print(json.dumps(lock_state(), indent=2))
print('== LEFTOVER PROCESSES ==')
print(json.dumps(processes(), indent=2))
try:
    print('== GPU ==')
    print(subprocess.run(
        ['nvidia-smi', '--query-gpu=temperature.gpu,memory.used,utilization.gpu',
         '--format=csv,noheader,nounits'],
        check=False, text=True, capture_output=True, timeout=30).stdout.strip())
except Exception as error:
    print(repr(error))

keys = [
    'passed', 'qualified', 'arm', 'optimizer_steps_before', 'inherited_Adam_steps',
    'actual_Adam_steps', 'new_Adam_steps', 'admitted_stage_rows',
    'suffix_stage_rows', 'total_native_stage_rows', 'normal_workers_shutdown',
    'checkpoint', 'checkpoint_sha256', 'error', 'partial_native_not_restorable',
]
for name in ['qualification', 'control-micro', 'candidate-micro', 'control-phase-1']:
    print(f'== STAGE {name} ==')
    print(json.dumps(stage_summary(name, keys), indent=2))

print('== CONTROLLER ==')
print(json.dumps(json_summary(RUN / 'RESULT.json', [
    'passed', 'qualification', 'arms', 'ability_promotion', 'error']), indent=2))
print('== CHECKPOINTS ==')
for name in ['control-phase-1/update-63.pt', 'control-phase-1/update-64.pt',
             'control-micro/update-62.pt', 'candidate-micro/update-62.pt']:
    path = RUN / name
    if path.exists():
        print(name)
        print(json.dumps(checkpoint_summary(path), indent=2))
