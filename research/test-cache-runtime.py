import json
import os
from pathlib import Path
import signal
import subprocess

folder = Path('/mnt/g/Heroes3-AI-Lab/research')
try:
    results = []
    for mode in ['plain', 'cached']:
        output = folder / f'ppo-cache-{mode}.json'
        command = ['bash', str(folder / 'run-lab.sh'), str(folder / 'train-ppo.py'),
                   '--workers', '12', '--updates', '2', '--inference-device', 'cuda', '--training-device', 'cuda',
                   '--checkpoint', '/mnt/g/Heroes3-AI-Lab/models/bc-balanced-v1/gnn.pt',
                   '--validation-report', str(folder / 'balanced-bc-gnn-validation.json'),
                   '--scenarios', str(folder / 'scenarios-v2.json'), '--output', str(output)]
        if mode == 'cached':
            command.append('--cache-next-value')
        with (folder / f'ppo-cache-{mode}.log').open('wb') as stream:
            subprocess.run(command, env=dict(os.environ, LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python'),
                           check=True, stdout=stream, stderr=subprocess.STDOUT, timeout=45)
        results.append(json.loads(output.read_text()))
    plain, cached = results
    for a, b in zip(plain['records'], cached['records']):
        assert a['actions_sha256'] == b['actions_sha256'] and a['returns_sha256'] == b['returns_sha256']
    (folder / 'ppo-cache-contract.json').write_text(json.dumps(dict(passed=True, actions_identical=True,
        returns_identical=True, worker_torch_imported=cached['worker_torch_imported'],
        uncached_seconds=plain['wall_seconds'], cached_seconds=cached['wall_seconds'],
        cached_pss_mib=cached['sampled_peak_total_pss_mib']), indent=2))
    print('Cached bootstrap runtime equivalence passed')
finally:
    for pid in [377, 299]:
        try:
            os.kill(pid, signal.SIGCONT)
        except ProcessLookupError:
            pass
