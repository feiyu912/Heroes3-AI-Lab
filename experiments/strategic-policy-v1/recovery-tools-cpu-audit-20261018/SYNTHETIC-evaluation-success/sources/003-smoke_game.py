"""Explicitly run one broker + native game. Importing/help never starts a game."""
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


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--map', default='Maps/adv/takeover-v2-train-01-mines')
    p.add_argument('--red', default='DirectorAI')
    p.add_argument('--blue', default='Nullkiller2')
    p.add_argument('--seed', type=int, default=2026101821)
    p.add_argument('--seconds', type=int, default=120)
    p.add_argument('--mode', choices=('heuristic', 'policy'), default='heuristic')
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--tag', default='strategic-broker-smoke-v1')
    args = p.parse_args()
    parent = Path('/root/heroes3-ai-lab/workers/strategy-agent-runs')
    parent.mkdir(parents=True, exist_ok=True)
    agent_dir = Path(tempfile.mkdtemp(prefix=f'{args.tag}-', dir=parent))
    broker_command = [sys.executable, str(ROOT / 'broker.py'), '--agent-dir', str(agent_dir),
                      '--mode', args.mode, '--idle-seconds', str(args.seconds + 60)]
    if args.checkpoint:
        broker_command += ['--checkpoint', str(args.checkpoint.resolve())]
    runner = ROOT.parent / 'adventure_runner_v5.py'
    game_command = [sys.executable, str(runner), '--agent-dir', str(agent_dir), '--map', args.map,
                    '--red', args.red, '--blue', args.blue, '--seed', str(args.seed),
                    '--seconds', str(args.seconds), '--tag', args.tag]
    plan = {'schema': 'strategic-broker-game-smoke-v1', 'agent_dir': str(agent_dir),
            'broker_command': broker_command, 'runner_command': game_command,
            'code_sha256': {str(path): digest(path) for path in
                [ROOT / 'broker.py', ROOT / 'encoder.py', ROOT / 'model.py', Path(__file__), runner]}}
    (agent_dir / 'smoke-plan.json').write_text(json.dumps(plan, indent=2))
    print('AGENT_DIR=' + str(agent_dir), flush=True)
    game_code, stdout = None, ''
    error = None
    with (agent_dir / 'broker.log').open('w') as broker_log:
        broker = subprocess.Popen(broker_command, stdout=broker_log, stderr=subprocess.STDOUT,
                                  start_new_session=True)
        try:
            deadline = time.monotonic() + 20
            while not (agent_dir / 'broker-ready.json').exists():
                if broker.poll() is not None:
                    raise RuntimeError('Broker exited before readiness')
                if time.monotonic() > deadline:
                    raise TimeoutError('Broker readiness timeout')
                time.sleep(.02)
            # The native runner itself owns the shared game-resource lock.
            completed = subprocess.run(game_command, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
            game_code, stdout = completed.returncode, completed.stdout
        except Exception as exception:
            error = repr(exception)
        finally:
            if broker.poll() is None:
                os.killpg(broker.pid, signal.SIGTERM)
                try:
                    broker.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(broker.pid, signal.SIGKILL)
                    broker.wait()
    (agent_dir / 'runner.log').write_text(stdout)
    requests = sorted(agent_dir.glob('request-????????.json'))
    actions = sorted(agent_dir.glob('action-????????.json'))
    trace = agent_dir / 'broker-trace.jsonl'
    events = [json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
    commits = [event for event in events if event.get('event') == 'decision_committed']
    responses = [event for event in events if event.get('event') == 'response_written']
    errors = [event for event in events if event.get('event') == 'protocol_error']
    request_ids = [int(path.stem.split('-')[1]) for path in requests]
    action_ids = [int(path.stem.split('-')[1]) for path in actions]
    integrity = []
    for event in commits:
        request_path, action_path = agent_dir / event['request_file'], agent_dir / event['action_file']
        integrity.append(request_path.is_file() and action_path.is_file()
                         and digest(request_path) == event['request_sha256']
                         and digest(action_path) == event['response_sha256'])
    match = re.search(r'^RUN_DIR=(.+)$', stdout, re.MULTILINE)
    native = None
    if match and (Path(match[1].strip()) / 'result.json').is_file():
        native = json.loads((Path(match[1].strip()) / 'result.json').read_text())
    passed = bool(game_code == 0 and native and native.get('completed') and requests
                  and request_ids == action_ids and len(commits) == len(requests)
                  and len(responses) == len(requests) and all(integrity) and not errors and not error)
    summary = {'schema': 'strategic-broker-smoke-result-v1', 'agent_dir': str(agent_dir),
               'passed': passed, 'runner_exit': game_code, 'broker_exit': broker.returncode,
               'error': error, 'request_ids': request_ids, 'action_ids': action_ids,
               'requests': len(requests), 'decisions_committed': len(commits),
               'responses_written': len(responses), 'protocol_errors': errors,
               'io_hashes_verified': bool(integrity) and all(integrity),
               'native_result': native, 'mode': args.mode,
               'limitations': 'Target selection protocol only; building/recruitment remain scripted. No strategic learning gain asserted.'}
    (agent_dir / 'smoke-result.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
