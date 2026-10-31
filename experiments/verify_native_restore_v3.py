"""Compare a native turn-start save reload with its original v3 policy game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
POLICY = ROOT / 'strategic-policy-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original-agent', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    original = json.loads((args.original_agent / 'smoke-result.json').read_text())
    native = original['native_result']
    assert original['passed'] and native['completed']
    save = Path(native['save_files'][0]['path'])
    config = native['config']
    directory = Path(tempfile.mkdtemp(prefix='restore-v3-', dir='/root/heroes3-ai-lab/workers/strategy-agent-runs'))
    files = [Path(__file__), args.checkpoint, save, ROOT / 'adventure_runner_v5.py']
    files += [POLICY / name for name in ['broker.py', 'model.py', 'encoder.py', 'supply_policy.py']]
    runtime = Path('/root/heroes3-ai-lab/src/vcmi-adv-build/bin')
    files += [runtime / name for name in ['vcmiclient', 'vcmiserver', 'libvcmi.so']]
    hashes = {str(p): sha(p) for p in files}
    plan = dict(hashes=hashes, original_agent=str(args.original_agent), original_native=native,
                agent_dir=str(directory), scope='Native turn-start boundary only; not mid-action or mid-battle restore')
    (args.out / 'plan.json').write_text(json.dumps(plan, indent=2))
    report = dict(status='running', passed=False, independent_ability_evaluation=False)
    broker = None
    try:
        with (args.out / 'broker.log').open('w') as log:
            broker = subprocess.Popen([sys.executable, str(POLICY / 'broker.py'), '--agent-dir', str(directory),
                '--mode', 'new-policy', '--checkpoint', str(args.checkpoint), '--idle-seconds', '300'],
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + 30
            while not (directory / 'broker-ready.json').exists():
                if broker.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Restore broker not ready')
                time.sleep(.02)
            command = [sys.executable, str(ROOT / 'adventure_runner_v5.py'), '--agent-dir', str(directory),
                '--save-file', str(save), '--map', config['map'], '--red', config['red'], '--blue', config['blue'],
                '--seed', str(config['seed']), '--seconds', '120', '--tag', args.out.name]
            runner = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            try:
                stdout, _ = runner.communicate(timeout=300)
            except BaseException:
                runner.terminate()
                try:
                    runner.communicate(timeout=12)
                except subprocess.TimeoutExpired:
                    runner.kill()
                    runner.communicate()
                raise
            result = subprocess.CompletedProcess(command, runner.returncode, stdout)
        (args.out / 'runner.log').write_text(result.stdout)
        match = re.search(r'^RUN_DIR=(.+)$', result.stdout, re.MULTILINE)
        if not match:
            raise RuntimeError('Restore runner missing evidence directory')
        run = Path(match[1])
        restored = json.loads((run / 'result.json').read_text())
        comparisons = {}
        for name in ['strategy-trace.jsonl', 'strategy-decisions.jsonl', 'strategy-trace.jsonl.targets.jsonl']:
            before, after = Path(native['run_dir']) / name, run / name
            comparisons[name] = dict(original_sha256=sha(before), restored_sha256=sha(after), equal=before.read_bytes() == after.read_bytes())
        io = []
        for before in sorted(args.original_agent.glob('request-????????.json')):
            after = directory / before.name
            io.append(after.exists() and sha(after) == sha(before) and
                      (directory / before.name.replace('request-', 'action-')).read_bytes() ==
                      (args.original_agent / before.name.replace('request-', 'action-')).read_bytes())
        equal_counts = len(io) == len(list(directory.glob('request-????????.json')))
        unchanged = all(sha(Path(p)) == h for p, h in hashes.items())
        passed = bool(result.returncode == 0 and restored.get('completed') and restored.get('native_load_verified')
            and native['winner'] == restored['winner'] and all(c['equal'] for c in comparisons.values())
            and io and all(io) and equal_counts and unchanged)
        report.update(status='completed', passed=passed, restored=restored, comparisons=comparisons,
            request_action_pairs=len(io), all_request_action_bytes_equal=all(io) and equal_counts,
            inputs_unchanged=unchanged, scope=plan['scope'])
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        if broker is not None and broker.poll() is None:
            os.killpg(broker.pid, signal.SIGTERM)
            try:
                broker.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(broker.pid, signal.SIGKILL)
                broker.wait()
        (args.out / 'result.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(passed=report['passed'], comparisons=report['comparisons'], pairs=report['request_action_pairs'])))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
