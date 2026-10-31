#!/usr/bin/env python3
"""CPU exact-request replay probe; divergence/boundary are invalid, never wins."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

from encoder import validate


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(request):
    return json.dumps({k: v for k, v in request.items() if k != 'request_id'},
                      sort_keys=True, separators=(',', ':'), allow_nan=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='Original rollout.jsonl; original request files must remain beside it')
    parser.add_argument('--out', type=Path, required=True, help='New, nonexistent evidence directory')
    parser.add_argument('--map', required=True)
    parser.add_argument('--red', default='DirectorAI')
    parser.add_argument('--blue', default='EmptyAI')
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--seconds', type=int, default=180)
    parser.add_argument('--max-decisions', type=int, default=0)
    parser.add_argument('--max-day', type=int, default=0)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    source_bytes = args.source.read_bytes()
    rows = []
    for line in source_bytes.splitlines():
        row = json.loads(line)
        req = validate(row['request'], row['request']['request_id'])
        old_file = args.source.parent / f"request-{req['request_id']:08d}.json"
        old_bytes = old_file.read_bytes()
        if digest(old_bytes) != row['request_sha256'] or json.loads(old_bytes) != req:
            raise ValueError(f'Original request hash/content mismatch: {old_file}')
        if not 0 <= row['action'] < len(req['candidates']):
            raise ValueError('Illegal original action')
        rows.append(row)
    directory = Path(tempfile.mkdtemp(prefix='exact-replay-', dir='/root/heroes3-ai-lab/workers/strategy-agent-runs'))
    runner = Path(__file__).resolve().parents[1] / 'adventure_runner_v5.py'
    command = [sys.executable, str(runner), '--map', args.map, '--red', args.red,
               '--blue', args.blue, '--seed', str(args.seed), '--seconds', str(args.seconds),
               '--agent-dir', str(directory), '--tag', args.out.name]
    plan = dict(source=str(args.source), source_sha256=digest(source_bytes), source_rows=len(rows),
                script_sha256=digest(Path(__file__).read_bytes()), command=command,
                agent_dir=str(directory), config={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                limitation='Exact original-action diagnostic replay; no gradient updates or effectiveness claims')
    (args.out / 'plan.json').write_text(json.dumps(plan, indent=2))
    print(json.dumps(plan), flush=True)
    matched = 0
    reason = 'runner_exited'
    stop = False
    def stopping(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, stopping)
    signal.signal(signal.SIGINT, stopping)
    with (args.out / 'runner.log').open('w') as log, (args.out / 'replay.jsonl').open('w') as audit:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while proc.poll() is None and not stop:
                path = directory / f'request-{matched + 1:08d}.json'
                if not path.exists():
                    time.sleep(.001)
                    continue
                raw = path.read_bytes()
                request = validate(json.loads(raw), matched + 1)
                if matched == len(rows):
                    reason = 'original_rollout_exhausted'
                    break
                expected = rows[matched]
                if canonical(request) != canonical(expected['request']):
                    reason = 'request_diverged'
                    (args.out / 'divergence.json').write_text(json.dumps(dict(index=matched,
                        actual=request, expected=expected['request'], actual_sha256=digest(raw)), indent=2))
                    break
                if args.max_day and request['day'] > args.max_day:
                    reason = 'day_boundary'
                    break
                if args.max_decisions and matched >= args.max_decisions:
                    reason = 'decision_boundary'
                    break
                response = directory / f'action-{matched + 1:08d}.json'
                if response.exists():
                    raise ValueError('Response already exists')
                temp = response.with_suffix('.tmp')
                temp.write_text(str(expected['action']) + '\n')
                os.replace(temp, response)
                audit.write(json.dumps(dict(index=matched, day=request['day'], action=expected['action'],
                    original_request_sha256=expected['request_sha256'], replay_request_sha256=digest(raw),
                    canonical_sha256=digest(canonical(request).encode()))) + '\n')
                audit.flush()
                matched += 1
                if args.max_decisions and matched >= args.max_decisions:
                    # The response is committed; native consumption is a separate
                    # post-run check and must not be inferred from this counter.
                    reason = 'decision_boundary'
                    time.sleep(.02)
                    break
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
    result = dict(valid=False, winner=None, diagnostic_only=True, reason='interrupted' if stop else reason,
                  matched_requests=matched, runner_exit=proc.returncode, agent_dir=str(directory),
                  source_unchanged=digest(args.source.read_bytes()) == plan['source_sha256'])
    (args.out / 'result.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
    return 0 if result['source_unchanged'] and reason in ('day_boundary', 'decision_boundary', 'original_rollout_exhausted') else 1


if __name__ == '__main__':
    raise SystemExit(main())
