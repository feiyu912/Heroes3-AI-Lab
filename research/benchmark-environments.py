import json
import os
from pathlib import Path
import statistics
import subprocess
import time
import argparse
import signal

parser = argparse.ArgumentParser()
parser.add_argument('--workers', type=int, nargs='+', default=[4, 8, 12, 16, 20])
parser.add_argument('--repeats', type=int, default=3)
parser.add_argument('--seconds', type=float, default=10)
parser.add_argument('--output', default='/mnt/g/Heroes3-AI-Lab/research/parallel-benchmark-v2.json')
args = parser.parse_args()
assert args.repeats > 0 and args.seconds > 0 and all(n > 0 for n in args.workers)

root = Path('/root/heroes3-ai-lab')
result_root = root / 'benchmarks'
result_root.mkdir(exist_ok=True)
records = []
run_id = str(time.time_ns())
suite_started = time.monotonic()


def system_memory():
    return {k: int(v.strip().split()[0]) / 1024
            for k, v in (line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
            if k in ['MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree']}


def memory(pid):
    values = {}
    try:
        for line in Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines():
            if ':' in line:
                name, value = line.split(':', 1)
                if name in ['Rss', 'Pss', 'Private_Clean', 'Private_Dirty']:
                    values[name] = int(value.strip().split()[0]) / 1024
    except (FileNotFoundError, ProcessLookupError):
        return 0.0, 0.0, 0.0
    return values.get('Rss', 0), values.get('Pss', 0), values.get('Private_Clean', 0) + values.get('Private_Dirty', 0)


for workers in args.workers:
    for repeat in range(args.repeats):
        group = f'{run_id}-n{workers}-r{repeat}'
        folder = result_root / group
        folder.mkdir(exist_ok=True)
        control = folder / 'control.json'
        # Fresh group paths must never contain an earlier start signal.
        if control.exists():
            group += '-' + str(time.time_ns())
            folder = result_root / group
            folder.mkdir()
            control = folder / 'control.json'
        processes = []
        streams = []
        group_started = time.monotonic()
        min_available = float('inf')
        max_swap_used = 0
        try:
            for index in range(workers):
                worker_root = root / 'workers' / group / str(index)
                env = dict(os.environ, LAB_WORKER_ROOT=str(worker_root))
                stream = (folder / f'{index}.log').open('wb')
                streams.append(stream)
                processes.append(subprocess.Popen(['bash', '/mnt/g/Heroes3-AI-Lab/research/run-battle-smoke.sh',
                                 '--benchmark', '--ready', str(folder / f'{index}.ready.json'),
                                 '--control', str(control), '--output', str(folder / f'{index}.json')],
                                 env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True))
            wait_until = time.monotonic() + 40
            while not all((folder / f'{i}.ready.json').exists() for i in range(workers)):
                assert time.monotonic() < wait_until, f'{group}: startup timeout'
                assert all(p.poll() is None for p in processes), f'{group}: worker failed at startup'
                time.sleep(0.1)
            ready = [json.loads((folder / f'{i}.ready.json').read_text()) for i in range(workers)]
            assert len({r['data_home'] for r in ready}) == workers
            start = time.monotonic() + 0.2
            control.write_text(json.dumps({'start': start, 'deadline': start + args.seconds}))
            peak_rss = peak_pss = peak_private = 0.0
            while any(p.poll() is None for p in processes):
                mem = system_memory()
                min_available = min(min_available, mem['MemAvailable'])
                max_swap_used = max(max_swap_used, mem['SwapTotal'] - mem['SwapFree'])
                assert mem['MemAvailable'] > 2048, 'WSL memory reserve below 2 GiB'
                assert max_swap_used < 256, 'Swap pressure exceeded 256 MiB'
                assert time.monotonic() < start + args.seconds + 20, f'{group}: runtime timeout'
                if time.monotonic() >= start:
                    samples = [memory(r['pid']) for r in ready]
                    peak_rss = max(peak_rss, sum(m[0] for m in samples))
                    peak_pss = max(peak_pss, sum(m[1] for m in samples))
                    peak_private = max(peak_private, sum(m[2] for m in samples))
                time.sleep(0.25)
            assert all(p.returncode == 0 for p in processes), f'{group}: nonzero exit code'
            data = [json.loads((folder / f'{i}.json').read_text()) for i in range(workers)]
            elapsed = max(d['ended'] for d in data) - min(d['started'] for d in data)
            cpu = sum(d['cpu_seconds'] for d in data)
            record = {'workers': workers, 'repeat': repeat, 'group': group,
                      'complete_group_wall_seconds': time.monotonic() - group_started,
                      'wsl_min_available_mib': min_available, 'wsl_max_swap_used_mib': max_swap_used,
                      'wall_seconds': elapsed,
                      'episodes': sum(d['episodes'] for d in data),
                      'steps': sum(d['steps'] for d in data),
                      'steps_per_second': sum(d['steps'] for d in data) / elapsed,
                      'battles_per_second': sum(d['episodes'] for d in data) / elapsed,
                      'cpu_core_equivalents': cpu / elapsed,
                      'cpu_percent_of_logical_capacity': 100 * cpu / elapsed / os.cpu_count(),
                      'sampled_peak_rss_sum_mib': peak_rss, 'sampled_peak_pss_sum_mib': peak_pss,
                      'sampled_peak_private_sum_mib': peak_private,
                      'mean_reset_ms': 1000 * sum(d['reset_seconds'] for d in data) / sum(d['episodes'] for d in data),
                      'mean_step_ms': 1000 * sum(d['step_seconds'] for d in data) / sum(d['steps'] for d in data),
                      'mean_policy_ms': 1000 * sum(d['decision_seconds'] for d in data) / sum(d['steps'] for d in data),
                      'all_exit_codes_zero': True, 'worker_records': data}
            records.append(record)
            print(json.dumps({k: v for k, v in record.items() if k != 'worker_records'}), flush=True)
            Path(args.output + '.progress.json').write_text(json.dumps(records, indent=2))
        finally:
            for process in processes:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
            for stream in streams:
                stream.close()

summary = []
for workers in args.workers:
    rows = [r for r in records if r['workers'] == workers]
    summary.append({'workers': workers,
                    'median_steps_per_second': statistics.median(r['steps_per_second'] for r in rows),
                    'min_steps_per_second': min(r['steps_per_second'] for r in rows),
                    'max_steps_per_second': max(r['steps_per_second'] for r in rows),
                    'max_sampled_pss_mib': max(r['sampled_peak_pss_sum_mib'] for r in rows),
                    'max_sampled_private_mib': max(r['sampled_peak_private_sum_mib'] for r in rows),
                    'median_reset_ms': statistics.median(r['mean_reset_ms'] for r in rows),
                    'median_cpu_core_equivalents': statistics.median(r['cpu_core_equivalents'] for r in rows)})
output = {'scope': f'Fixed 20-vs-10 archers, no magic, BattleAI, diagnostic Python policy, {args.seconds}s per point, {args.repeats} repeats, default CPU scheduling; no neural inference or learning',
          'suite_wall_seconds': time.monotonic() - suite_started,
          'logical_cpus_visible': os.cpu_count(), 'summary': summary, 'runs': records}
Path(args.output).write_text(json.dumps(output, indent=2))
print('BENCHMARK COMPLETE', json.dumps(summary), flush=True)
