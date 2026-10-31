import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--workers', nargs='+', type=int, default=[4, 8, 12, 16, 20])
parser.add_argument('--repeats', type=int, default=2)
parser.add_argument('--updates', type=int, default=6)
parser.add_argument('--output', default='/mnt/g/Heroes3-AI-Lab/research/training-device-grid.json')
parser.add_argument('--fixed-scene', action='store_true')
args = parser.parse_args()
folder = Path('/root/heroes3-ai-lab/benchmarks') / ('training-' + str(time.time_ns()))
folder.mkdir()
records = []
started = time.monotonic()
for repeat in range(args.repeats):
    for workers in args.workers:
        modes = [('cpu', 'cpu'), ('cpu', 'cuda'), ('cuda', 'cuda')]
        if repeat % 2:
            modes.reverse()
        for inference, training in modes:
            name = f'{workers}-{repeat}-{inference}-{training}'
            result_path = folder / (name + '.json')
            env = dict(os.environ, LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',
                       LAB_WORKER_ROOT='/root/heroes3-ai-lab/workers/' + folder.name + '-' + name)
            with (folder / (name + '.log')).open('wb') as stream:
                command = ['bash', '/mnt/g/Heroes3-AI-Lab/research/run-lab.sh',
                                         '/mnt/g/Heroes3-AI-Lab/research/train-ppo.py',
                                         '--workers', str(workers), '--updates', str(args.updates),
                                         '--inference-device', inference, '--training-device', training,
                                         '--output', str(result_path)]
                if args.fixed_scene:
                    command += ['--fixed-map', 'lab/smoke.vmap', '--fixed-role', 'attacker', '--cache-next-value']
                result = subprocess.run(command, env=env, stdout=stream,
                                        stderr=subprocess.STDOUT, timeout=180)
            assert result.returncode == 0, str(folder / (name + '.log'))
            data = json.loads(result_path.read_text())
            assert data['completed'] and data['all_workers_exit_zero']
            steady = data['records'][1:]
            steps = sum(r['steps'] for r in steady)
            wall = sum(r['rollout_seconds'] + r['update_seconds'] for r in steady)
            record = dict(workers=workers, repeat=repeat, inference=inference, training=training,
                          steady_steps_per_second=steps/wall, complete_steps_per_second=sum(r['steps'] for r in data['records'])/data['wall_seconds'],
                          boot_seconds=data['boot_seconds'], pss_peak_mib=data['sampled_peak_total_pss_mib'],
                          gpu_peak_allocated_mib=data['gpu_peak_allocated_mib'], result=str(result_path),
                          episodes=data['records'][-1]['episodes_total'], truncations=data['records'][-1]['truncations_total'])
            records.append(record)
            Path(args.output + '.progress.json').write_text(json.dumps(records, indent=2))
            print(json.dumps(record), flush=True)
summary = []
for n in args.workers:
    for inference, training in [('cpu', 'cpu'), ('cpu', 'cuda'), ('cuda', 'cuda')]:
        rows = [r for r in records if r['workers'] == n and r['inference'] == inference and r['training'] == training]
        summary.append(dict(workers=n, inference=inference, training=training,
                            median_steps_per_second=statistics.median(r['steady_steps_per_second'] for r in rows),
                            min_steps_per_second=min(r['steady_steps_per_second'] for r in rows),
                            max_steps_per_second=max(r['steady_steps_per_second'] for r in rows),
                            peak_pss_mib=max(r['pss_peak_mib'] for r in rows)))
Path(args.output).write_text(json.dumps(dict(scope='Fixed20-vs10archers every worker; cached next value; optimized NumPy-only workers' if args.fixed_scene else 'Existing v1 training curriculum; case mixture changes across worker counts, exploratory only',
                                           wall_seconds=time.monotonic()-started, summary=summary, records=records), indent=2))
