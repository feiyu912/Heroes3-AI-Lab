#!/usr/bin/env python3
"""Prepare or explicitly execute sequential native training boundary comparison.

Default prepares a unique immutable plan only. --execute starts real CUDA/game
training. No curriculum results from this harness establish policy improvement.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
LAB = Path('/root/heroes3-ai-lab')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False))
    temporary.replace(path)


def frozen_inputs(initial):
    inputs = [Path(__file__), initial, HERE / 'checkpoints/prior-initial-v2.pt']
    inputs += [HERE / name for name in ('train_ppo_pilot.py', 'encoder.py', 'model.py')]
    inputs += [HERE.parent / 'adventure_runner_v5.py']
    runtime = LAB / 'src/vcmi-adv-build/bin'
    inputs += [runtime / name for name in ('vcmiclient', 'vcmiserver', 'libvcmi.so')]
    inputs += [path for path in (runtime / 'config').rglob('*') if path.is_file()]
    director = LAB / 'src/vcmi-adv/AI/DirectorAI'
    inputs += list(director.glob('*.cpp')) + list(director.glob('*.h'))
    inputs += [LAB / 'data/vcmi/Maps/adv' / (name + '.vmap') for name in
               ('takeover-v2-train-01-mines', 'takeover-v2-train-02-development')]
    return {str(path.resolve()): sha(path) for path in inputs}


def assert_frozen(hashes):
    changed = [path for path, digest in hashes.items() if not Path(path).is_file() or sha(path) != digest]
    if changed:
        raise RuntimeError('Frozen boundary-comparison inputs changed: ' + ', '.join(changed))


def process_table():
    rows = {}
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit():
            continue
        try:
            stat = (directory / 'stat').read_text()
            fields = stat[stat.rindex(')') + 2:].split()
            rows[int(directory.name)] = dict(pid=int(directory.name), parent=int(fields[1]),
                start=fields[19], state=fields[0], rss_bytes=int(fields[21]) * os.sysconf('SC_PAGE_SIZE'))
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            pass
    return rows


def descendants(root, table):
    selected = {root} if root in table else set()
    while True:
        expanded = selected | {pid for pid, row in table.items() if row['parent'] in selected}
        if expanded == selected:
            return {pid: table[pid] for pid in selected}
        selected = expanded


def alive(identities, table):
    return {pid: row for pid, row in table.items() if pid in identities and
            row['start'] == identities[pid] and row['state'] != 'Z'}


def stop_owned(identities):
    # Identity checks prevent killing reused PIDs. Includes descendants that
    # created their own process sessions, which killpg alone would miss.
    for sig, wait in ((signal.SIGTERM, 8), (signal.SIGKILL, 2)):
        running = alive(identities, process_table())
        for pid in sorted(running, reverse=True):
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        deadline = time.monotonic() + wait
        while alive(identities, process_table()) and time.monotonic() < deadline:
            time.sleep(.1)
    return list(alive(identities, process_table()))


def gpu_sample():
    command = ['nvidia-smi', '--query-gpu=index,memory.used,utilization.gpu', '--format=csv,noheader,nounits']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=3)
        if result.returncode:
            return dict(available=False, error=result.stderr.strip()[:200])
        return dict(available=True, devices=[dict(index=int(row[0]), used_memory_mib=float(row[1]),
                    utilization_percent=float(row[2])) for line in result.stdout.splitlines()
                    if (row := [x.strip() for x in line.split(',')]) and len(row) == 3])
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        return dict(available=False, error=repr(error))


def run_stage(stage, out, hashes, seconds):
    assert_frozen(hashes)
    identities, samples = {}, []
    start = time.monotonic()
    code, error = None, None
    with (out / (stage['name'] + '.log')).open('w') as log:
        process = subprocess.Popen(stage['command'], stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        try:
            while True:
                table = process_table()
                tree = descendants(process.pid, table)
                identities.update({pid: row['start'] for pid, row in tree.items()})
                tracked = alive(identities, table)
                sample = dict(elapsed_seconds=time.monotonic() - start,
                              tree_rss_bytes=sum(row['rss_bytes'] for row in tracked.values()),
                              live_processes=len(tracked), gpu=gpu_sample())
                samples.append(sample)
                with (out / (stage['name'] + '-resources.jsonl')).open('a') as resource_log:
                    resource_log.write(json.dumps(sample) + '\n')
                if process.poll() is not None:
                    code = process.returncode
                    break
                if time.monotonic() - start > seconds:
                    raise TimeoutError('Boundary training stage exceeded configured wall budget')
                time.sleep(1)
        except BaseException as caught:
            error = repr(caught)
            raise
        finally:
            leftovers = alive(identities, process_table())
            survivors = stop_owned(identities) if leftovers else []
            if process.poll() is None:
                process.wait(timeout=3)
            stage_report = dict(name=stage['name'], command=stage['command'], exit_code=code,
                error=error, wall_seconds=time.monotonic() - start,
                peak_tree_rss_bytes=max((sample['tree_rss_bytes'] for sample in samples), default=None),
                peak_device_gpu_memory_mib=max((device['used_memory_mib'] for sample in samples
                    for device in sample['gpu'].get('devices', [])), default=None),
                resource_scope='Tree RSS sums shared pages; GPU memory is device-wide, includes other desktop processes.',
                leftover_owned_processes_after_exit=list(leftovers), survivors_after_cleanup=survivors)
            atomic_json(out / (stage['name'] + '-stage.json'), stage_report)
    if code != 0 or stage_report['leftover_owned_processes_after_exit']:
        raise RuntimeError('Training stage failed or left owned processes; see stage report')
    assert_frozen(hashes)
    training = json.loads((Path(stage['directory']) / 'training.json').read_text())
    if training.get('status') != 'completed':
        raise RuntimeError('Trainer did not certify complete stage')
    stage_report['training'] = {key: training.get(key) for key in
        ('CUDA_training', 'optimizer_steps_this_run', 'optimizer_steps_total', 'lineage', 'updates')}
    atomic_json(out / (stage['name'] + '-stage.json'), stage_report)
    return stage_report


def differences(left, right, path='root', limit=20):
    import torch
    result = []
    def visit(a, b, key):
        if len(result) >= limit:
            return
        if isinstance(a, torch.Tensor):
            if not isinstance(b, torch.Tensor) or a.shape != b.shape or a.dtype != b.dtype or not torch.equal(a, b):
                result.append(dict(path=key, reason='tensor differs', shape=list(a.shape),
                    max_abs_delta=float((a.double() - b.double()).abs().max())
                    if isinstance(b, torch.Tensor) and a.shape == b.shape and a.numel() else None))
        elif isinstance(a, dict) and isinstance(b, dict):
            if a.keys() != b.keys():
                result.append(dict(path=key, reason='dictionary keys differ'))
            for child in a.keys() & b.keys():
                visit(a[child], b[child], key + '.' + str(child))
        elif isinstance(a, (list, tuple)) and isinstance(b, type(a)):
            if len(a) != len(b):
                result.append(dict(path=key, reason='sequence lengths differ', left=len(a), right=len(b)))
            for index, (x, y) in enumerate(zip(a, b)):
                visit(x, y, key + '[' + str(index) + ']')
                if len(result) >= limit:
                    break
        elif type(a) is not type(b) or a != b:
            result.append(dict(path=key, reason='value differs', left=repr(a)[:200], right=repr(b)[:200]))
    visit(left, right, path)
    return result


def load_bundle(path):
    import torch
    raw = path.read_bytes()
    return torch.load(io.BytesIO(raw), map_location='cpu', weights_only=True), hashlib.sha256(raw).hexdigest()


def compare(root):
    checks, bundles = {}, {}
    for update, left, right in ((1, 'continuous-2', 'split-1'), (2, 'continuous-2', 'resume-2')):
        a, ash = load_bundle(root / left / f'update-{update}.pt')
        b, bsh = load_bundle(root / right / f'update-{update}.pt')
        keys = ('state_dict', 'optimizer', 'torch_rng', 'cuda_rng', 'python_rng', 'training_updates',
                'optimizer_steps_total', 'complete_update_boundary', 'protocol_sha256', 'protocol')
        diff = differences({key: a[key] for key in keys}, {key: b[key] for key in keys})
        valid = (a.get('complete_update_boundary') is True and b.get('complete_update_boundary') is True and
                 a.get('training_updates') == b.get('training_updates') == update)
        checks[f'checkpoint_update_{update}'] = dict(equal=not diff and valid, differences=diff,
            complete_boundary_metadata_valid=valid,
            left_sha256=ash, right_sha256=bsh,
            note='Serialized hashes may differ because lineage and output plan differ; compare semantic tensors/state.')
        bundles[(left, update)], bundles[(right, update)] = a, b
    boundary = root / 'split-1/update-1.pt'
    resumed = bundles[('resume-2', 2)]
    checks['resume_lineage'] = dict(equal=resumed['lineage']['mode'] == 'resume' and
        resumed['lineage']['parent_sha256'] == sha(boundary) and
        not resumed['lineage']['reset_optimizer'] and not resumed['lineage']['reset_rng'],
        lineage=resumed['lineage'])
    for update in (1, 2):
        branch = 'split-1' if update == 1 else 'resume-2'
        for episode in range(4):
            left = json.loads((root / 'continuous-2' / f'update-{update}-episode-{episode}/episode.json').read_text())
            right = json.loads((root / branch / f'update-{update}-episode-{episode}/episode.json').read_text())
            semantic = lambda record: {key: record.get(key) for key in
                ('config', 'valid', 'reward', 'decisions', 'native_consumption_verified')}
            native_keys = ('winner', 'completed', 'actual_ai', 'moves_requested', 'move_replies',
                           'changed_tile_replies', 'failed_move_replies', 'turns')
            diff = differences(dict(semantic(left), native={key: left['native'].get(key) for key in native_keys}),
                               dict(semantic(right), native={key: right['native'].get(key) for key in native_keys}))
            traces = {}
            for name, base in (('rollout', 'rollout_dir'), ('native_decisions', None)):
                paths = [Path(record[base]) / 'rollout.jsonl' if base else
                         Path(record['native']['run_dir']) / 'strategy-decisions.jsonl' for record in (left, right)]
                rows = [[json.loads(line) for line in path.read_text().splitlines()] for path in paths]
                trace_diff = differences(rows[0], rows[1])
                traces[name] = dict(equal=not trace_diff, left_records=len(rows[0]), right_records=len(rows[1]),
                                    differences=trace_diff)
            valid = all(record.get('valid') is True and record.get('native_consumption_verified') is True and
                        record['native'].get('completed') is True and record.get('reward') in (-1., 1.)
                        for record in (left, right))
            checks[f'update_{update}_episode_{episode}'] = dict(
                equal=not diff and valid and all(t['equal'] for t in traces.values()),
                valid_completed_native_games=valid, differences=diff, traces=traces)
    training = {name: json.loads((root / name / 'training.json').read_text())
                for name in ('continuous-2', 'split-1', 'resume-2')}
    checks['training_stages_completed'] = dict(equal=all(data.get('status') == 'completed' for data in training.values()))
    return dict(passed=all(check['equal'] for check in checks.values()), checks=checks,
                training_summaries={name: {key: data.get(key) for key in
                    ('status', 'CUDA_training', 'optimizer_steps_this_run', 'optimizer_steps_total', 'lineage', 'updates')}
                    for name, data in training.items()},
                scope='Native same-protocol complete-update reproducibility; no independent ability evaluation.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path, help='New unique harness output directory')
    parser.add_argument('--initialize-from', type=Path, default=HERE / 'ppo-pilot-02/update-2.pt')
    parser.add_argument('--execute', action='store_true', help='Explicitly run real sequential CUDA/native training')
    parser.add_argument('--compare-root', type=Path, help='Only compare an existing completed harness root')
    parser.add_argument('--stage-seconds', type=int, default=1800)
    args = parser.parse_args()
    if args.compare_root and args.execute:
        parser.error('--compare-root and --execute are mutually exclusive')
    if args.stage_seconds < 1:
        parser.error('--stage-seconds must be positive')
    args.out.mkdir(parents=True, exist_ok=False)
    if args.compare_root:
        report = compare(args.compare_root.resolve())
        atomic_json(args.out / 'comparison.json', report)
        return 0 if report['passed'] else 1
    out = args.out.resolve()
    trainer = HERE / 'train_ppo_pilot.py'
    stages = []
    for name, updates, origin in [('continuous-2', 2, ['--initialize-from', str(args.initialize_from.resolve())]),
                                 ('split-1', 1, ['--initialize-from', str(args.initialize_from.resolve())]),
                                 ('resume-2', 2, ['--resume', str(out / 'split-1/update-1.pt')])]:
        stages.append(dict(name=name, directory=str(out / name), command=[sys.executable, str(trainer),
            '--out', str(out / name), '--updates', str(updates)] + origin))
    hashes = frozen_inputs(args.initialize_from.resolve())
    plan = dict(schema='strategic-native-boundary-comparison-v1', hashes=hashes, stages=stages,
        parent_checkpoint_sha256=sha(args.initialize_from), execute_requested=args.execute,
        resource_policy='Exactly one sequential learner; trainer owns GPU lock, runner owns shared simulation lock.',
        limits='16 curriculum games: continuous 8, split 4, resume next 4. No dev/test; no promotion claim.',
        stage_wall_budget_seconds=args.stage_seconds)
    atomic_json(out / 'plan.json', plan)
    snapshot = out / 'sources'
    snapshot.mkdir()
    for index, filename in enumerate(hashes):
        path = Path(filename)
        if path.suffix in ('.py', '.cpp', '.h', '.json'):
            shutil.copy2(path, snapshot / f'{index:03d}-{path.name}')
    report = dict(status='prepared', game_started=False, stages=[])
    atomic_json(out / 'status.json', report)
    if not args.execute:
        print(json.dumps(dict(status='prepared_only', plan=str(out / 'plan.json'), game_started=False)))
        return 0
    def interrupted(signum, frame):
        raise InterruptedError('Boundary harness received termination signal')
    previous = {sig: signal.signal(sig, interrupted) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        report.update(status='running', game_started=True)
        atomic_json(out / 'status.json', report)
        for stage in stages:
            report['stages'].append(run_stage(stage, out, hashes, args.stage_seconds))
            atomic_json(out / 'status.json', report)
            print(json.dumps(dict(completed_stage=stage['name'])), flush=True)
        result = compare(out)
        atomic_json(out / 'comparison.json', result)
        report.update(status='completed' if result['passed'] else 'comparison_failed', boundary_equal=result['passed'])
        return 0 if result['passed'] else 1
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        try:
            atomic_json(out / 'status.json', report)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
