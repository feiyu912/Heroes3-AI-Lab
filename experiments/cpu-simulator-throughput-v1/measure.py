#!/usr/bin/env python3
"""CPU simulation capacity protocol; defaults to preparation only, no game launch."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid

HERE = Path(__file__).resolve().parent
LAB = Path('/root/heroes3-ai-lab')
SCALES = [1, 2, 4, 8, 12, 24]
MAPS = ['Maps/adv/takeover-v2-train-01-mines', 'Maps/adv/takeover-v2-train-02-development']
MIB = 1024 * 1024


def write(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2))
    os.replace(temp, path)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(MIB), b''):
            h.update(chunk)
    return h.hexdigest()


def memory():
    data = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        data[key] = int(value.split()[0]) * 1024
    data['SwapUsed'] = data['SwapTotal'] - data['SwapFree']
    data['disk_free'] = os.statvfs('/root').f_bavail * os.statvfs('/root').f_frsize
    return data


def batch_processes(token):
    found = []
    match = ('LAB_THROUGHPUT_BATCH=' + token).encode()
    for path in Path('/proc').glob('[0-9]*/environ'):
        try:
            if match not in path.read_bytes().split(b'\0'):
                continue
            pid = int(path.parent.name)
            stat = (path.parent / 'stat').read_text().rsplit(')', 1)[1].split()
            status = (path.parent / 'status').read_text().splitlines()
            rss = next((int(v.split()[1])*1024 for v in status if v.startswith('VmRSS:')), 0)
            pss = None
            try:
                pss = next(int(v.split()[1])*1024 for v in (path.parent / 'smaps_rollup').read_text().splitlines() if v.startswith('Pss:'))
            except (OSError, StopIteration):
                pass
            found.append(dict(pid=pid, group=int(stat[2]), rss=rss, pss=pss,
                              threads=next((int(v.split()[1]) for v in status if v.startswith('Threads:')), 0),
                              cpu_ticks=int(stat[11])+int(stat[12])))
        except (OSError, ValueError, IndexError, StopIteration):
            continue
    return found


def clean(procs, token):
    for proc in procs:
        if proc.poll() is None:
            proc.terminate()
    deadline = time.monotonic() + 10
    while any(proc.poll() is None for proc in procs) and time.monotonic() < deadline:
        time.sleep(.05)
    # Independent native sessions are identified by inherited unique batch token,
    # never by executable name or a reusable unverified PID file.
    for entry in batch_processes(token):
        try:
            os.killpg(entry['group'], signal.SIGKILL)
        except ProcessLookupError:
            pass
    for proc in procs:
        if proc.poll() is None:
            proc.kill()
        proc.wait()


def check_frozen(hashes):
    return all(path.exists() and sha(path) == value for path, value in hashes.items())


def synthetic_lab(out, fail):
    root = Path(tempfile.mkdtemp(prefix='throughput-synthetic-'))
    binary = root / 'src/vcmi-adv-build/bin'
    for p in (binary / 'config', root / 'data/vcmi/Maps/adv', root / 'data/vcmi/Data', root / 'data/vcmi/Mods', root / 'evaluations'):
        p.mkdir(parents=True)
    for name in MAPS:
        (root / ('data/vcmi/' + name + '.vmap')).write_text('synthetic only')
    for name in ('vcmiserver', 'libvcmi.so'):
        (binary / name).write_text('synthetic only')
    engine = binary / 'vcmiclient'
    engine.write_text('#!' + sys.executable + '''
import os, signal, time
from pathlib import Path
allocation = bytearray(12*1024*1024)
child = os.fork()
if child == 0:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True: time.sleep(1)
Path('synthetic-child.pid').write_text(str(child))
print('Player red will be lead by ' + os.environ['LAB_ADV_AI_0'], flush=True)
print('Player blue will be lead by ' + os.environ['LAB_ADV_AI_1'], flush=True)
time.sleep(1.5)
if os.environ.get('LAB_SYNTHETIC_FAIL') == '1': raise SystemExit(7)
print('DirectorAI: native gameOver player=red victory=1 loss=0', flush=True)
print('All players have ended the game.', flush=True)
''')
    engine.chmod(0o755)
    return root


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--execute', action='store_true', help='Explicit scheduling switch; default only prepares protocol')
    p.add_argument('--stages', default='1,2,4,8,12,24')
    p.add_argument('--repeats', type=int, default=4, help='Games per slot; real runs require multiples of 4 to balance both maps/roles')
    p.add_argument('--seconds', type=int, default=90)
    p.add_argument('--synthetic', action='store_true', help='Fake processes in private /tmp lab; never real pool/game/GPU')
    p.add_argument('--inject-failure', action='store_true', help='Synthetic-only native exit failure')
    args = p.parse_args()
    stages = list(map(int, args.stages.split(',')))
    if stages != SCALES[:len(stages)] or args.repeats < 1:
        raise ValueError('Stages must be a prefix of 1,2,4,8,12,24; repeats >= 1')
    if args.inject_failure and not args.synthetic:
        raise ValueError('Failure injection is synthetic only')
    if not args.synthetic and args.repeats % 4:
        raise ValueError('Real throughput repeats must be a multiple of 4 for equal map/role composition')
    args.out.mkdir(parents=True, exist_ok=False)
    token = uuid.uuid4().hex
    lab = synthetic_lab(args.out, args.inject_failure) if args.synthetic and args.execute else LAB
    binary = lab / 'src/vcmi-adv-build/bin'
    inputs = [HERE / 'measure.py', HERE / 'worker_runner.py']
    inputs += [binary / n for n in ('vcmiclient', 'vcmiserver', 'libvcmi.so')]
    inputs += list((lab / 'src/vcmi-adv/AI/DirectorAI').glob('*.[ch]*'))
    inputs += [lab / ('data/vcmi/' + m + '.vmap') for m in MAPS]
    hashes = {path: sha(path) for path in inputs}
    initial = memory()
    gates = dict(min_available_bytes=max(2048*MIB, int(initial['MemTotal']*.20)), max_swap_growth_bytes=256*MIB,
                 min_disk_free_bytes=5*1024*MIB, max_batch_rss_fraction=.70, next_stage_safety_factor=1.25,
                 next_stage_available_reserve_fraction=.20,
                 escalation='All jobs valid, no stale processes, no input change, and capacity prediction passes; otherwise stop and diagnose')
    plan = dict(schema='cpu-simulator-throughput-v1', execute=args.execute, synthetic=args.synthetic,
                token=token, lab=str(lab), stages=stages, repeats=args.repeats, maps=MAPS,
                hashes={str(k):v for k,v in hashes.items()}, gates=gates, initial_memory=initial,
                original_runner_snapshot_sha256='b786989e0a91b910ecd0fd0138136f77fbf83187ca2f8a4dde58472050246846',
                claim='CPU native-game throughput only; no GPU learner, no parallel PPO, no policy-quality inference')
    write(args.out / 'protocol.json', plan)
    if not args.execute:
        print(json.dumps(dict(status='prepared_only', protocol=str(args.out/'protocol.json'))))
        return 0
    stop = False
    def requested_stop(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, requested_stop)
    signal.signal(signal.SIGINT, requested_stop)
    report = dict(status='running', synthetic=args.synthetic, stages=[])
    lock_path = lab / 'evaluations/.pool-lock'
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            report.update(status='blocked_pool_lock', reason='Another batch owns the simulator pool; no games launched')
            write(args.out/'result.json', report)
            return 2
        identity = os.fstat(lock.fileno())
        # A separate open description must fail even before any worker starts.
        with lock_path.open('a') as contender:
            try:
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                report['competitor_excluded'] = True
            else:
                raise RuntimeError('Pool lock exclusion failed')
        write(args.out/'supervisor-ready.json', dict(pid=os.getpid(), lock=str(lock_path), token=token,
              device=identity.st_dev, inode=identity.st_ino))
        previous = None
        for scale in stages:
            if stop:
                report.update(status='interrupted')
                break
            before = memory()
            if before['MemAvailable'] < gates['min_available_bytes'] or before['disk_free'] < gates['min_disk_free_bytes'] or before['SwapUsed']-initial['SwapUsed'] > gates['max_swap_growth_bytes']:
                report.update(status='capacity_gate', reason='Resources below launch reserve before stage', rejected_scale=scale)
                break
            if previous and before['MemAvailable'] - previous['peak_batch_rss']/previous['scale']*scale*1.25 < gates['min_available_bytes']:
                report.update(status='capacity_gate', reason='Conservative next-scale RSS estimate would consume reserved available RAM', rejected_scale=scale)
                break
            stage_dir = args.out / f'scale-{scale:02d}'
            stage_dir.mkdir()
            jobs = []
            processes = []
            active = []
            stage = dict(scale=scale, jobs=jobs, peak_batch_rss=0, peak_batch_pss=0, min_available=before['MemAvailable'], max_swap_growth=0)
            start = time.monotonic()
            reason = None
            try:
                with (stage_dir/'resources.jsonl').open('w') as samples:
                    next_job = 0
                    while next_job < scale*args.repeats or active:
                        if stop:
                            reason = 'supervisor_interrupted'
                            break
                        if not check_frozen(hashes):
                            reason = 'frozen_input_changed'
                            break
                        while next_job < scale*args.repeats and len(active) < scale:
                            number = next_job
                            job_dir = stage_dir/f'job-{number:03d}'
                            job_dir.mkdir()
                            red, blue = ('DirectorAI','Nullkiller2') if number%2 == 0 else ('Nullkiller2','DirectorAI')
                            cmd = [sys.executable, str(HERE/'worker_runner.py'), '--map', MAPS[(number//2)%2], '--red', red, '--blue', blue,
                                   '--seed', str(2026102100+number%4), '--seconds', str(args.seconds), '--tag', f'throughput-{token[:8]}-{scale}-{number}',
                                   '--pool-lock-fd', str(lock.fileno()), '--pool-lock-dev', str(identity.st_dev), '--pool-lock-inode', str(identity.st_ino),
                                   '--report-dir', str(job_dir), '--native-pid-file', str(job_dir/'native-pid.json'), '--lab-root', str(lab)]
                            env = dict(os.environ, LAB_THROUGHPUT_BATCH=token, LAB_THROUGHPUT_JOB=str(number), OMP_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='')
                            if args.inject_failure:
                                env['LAB_SYNTHETIC_FAIL'] = '1'
                            with (job_dir/'worker.log').open('w') as log:
                                proc = subprocess.Popen(cmd, env=env, pass_fds=(lock.fileno(),), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                            processes.append(proc)
                            active.append((proc, job_dir))
                            next_job += 1
                        mem = memory()
                        entries = batch_processes(token)
                        rss = sum(e['rss'] for e in entries)
                        pss = sum(e['pss'] or 0 for e in entries)
                        stage['peak_batch_rss'] = max(stage['peak_batch_rss'], rss)
                        stage['peak_batch_pss'] = max(stage['peak_batch_pss'], pss)
                        stage['min_available'] = min(stage['min_available'], mem['MemAvailable'])
                        stage['max_swap_growth'] = max(stage['max_swap_growth'], mem['SwapUsed']-initial['SwapUsed'])
                        samples.write(json.dumps(dict(seconds=time.monotonic()-start, memory=mem, batch_rss=rss, batch_pss=pss,
                            load_average=os.getloadavg(), batch_threads=sum(e['threads'] for e in entries), processes=entries))+'\n')
                        samples.flush()
                        if mem['MemAvailable'] < gates['min_available_bytes']:
                            reason = 'available_memory_gate'
                        elif mem['SwapUsed']-initial['SwapUsed'] > gates['max_swap_growth_bytes']:
                            reason = 'swap_growth_gate'
                        elif mem['disk_free'] < gates['min_disk_free_bytes']:
                            reason = 'disk_space_gate'
                        elif rss > initial['MemTotal']*.70:
                            reason = 'batch_rss_gate'
                        for proc, job_dir in list(active):
                            if proc.poll() is None:
                                continue
                            result_files = [f for f in job_dir.glob('*.json') if f.name != 'native-pid.json']
                            native = json.loads(result_files[0].read_text()) if len(result_files) == 1 else None
                            valid = proc.returncode == 0 and native is not None and native.get('completed') and native.get('inputs_unchanged')
                            jobs.append(dict(directory=str(job_dir), exit=proc.returncode, valid=bool(valid), native=native))
                            active.remove((proc, job_dir))
                            if not valid:
                                reason = 'invalid_native_job'
                        if reason:
                            break
                        time.sleep(.20)
            except Exception as error:
                reason = 'supervisor_exception'
                stage['exception'] = repr(error)
            finally:
                clean(processes, token)
            stage['wall_seconds'] = time.monotonic()-start
            stage['remaining_processes'] = batch_processes(token)
            stage['inputs_unchanged'] = check_frozen(hashes)
            stage['valid_jobs'] = sum(j['valid'] for j in jobs)
            stage['completed_all'] = len(jobs) == scale*args.repeats and stage['valid_jobs'] == len(jobs)
            stage['failure'] = reason or ('stale_processes' if stage['remaining_processes'] else None)
            stage['games_per_second'] = stage['valid_jobs']/stage['wall_seconds'] if stage['completed_all'] and not stage['failure'] else None
            write(stage_dir/'result.json', stage)
            report['stages'].append(stage)
            write(args.out/'result.json', report)
            if stage['failure'] or not stage['completed_all'] or not stage['inputs_unchanged']:
                report.update(status='failed_gate', reason=stage['failure'] or 'incomplete_or_changed')
                break
            if previous and stage['games_per_second'] < previous['games_per_second']*.8:
                report.update(status='capacity_gate', reason='Throughput fell >20% from previous scale; repeat/diagnose before escalating', rejected_next_stage=True)
                break
            previous = stage
        else:
            report['status'] = 'completed_requested_scales'
    report['all_batch_processes_gone'] = not batch_processes(token)
    report['claim'] = plan['claim']
    write(args.out/'result.json', report)
    print(json.dumps(dict(status=report['status'], stages=len(report['stages']), output=str(args.out))))
    return 0 if report['status'] == 'completed_requested_scales' and report['all_batch_processes_gone'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
