"""Per-game atomic candidate broker. Heuristic mode has no torch dependency."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import time
from encoder import ENCODER_VERSION, validate

FILE = re.compile(r'^request-(\d{8})\.json$')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def atomic(path, data):
    temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
    with temporary.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def append_trace(path, event):
    with path.open('a') as stream:
        stream.write(json.dumps(event, allow_nan=False, separators=(',', ':')) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--agent-dir', type=Path, required=True)
    p.add_argument('--mode', choices=('heuristic', 'policy'), default='heuristic')
    p.add_argument('--checkpoint', type=Path)
    p.add_argument('--poll-ms', type=int, default=10)
    p.add_argument('--idle-seconds', type=float, default=300)
    p.add_argument('--max-requests', type=int, default=0)
    args = p.parse_args()
    directory = args.agent_dir.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    lock = (directory / 'broker.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    trace = directory / 'broker-trace.jsonl'
    model = None
    model_version = 'heuristic-score-argmax-v1'
    if args.mode == 'policy':
        if not args.checkpoint:
            raise ValueError('--checkpoint is required for policy mode; no silent random policy')
        import torch
        from model import load_checkpoint
        torch.set_num_threads(1)
        model = load_checkpoint(args.checkpoint, 'cpu')
        model_version = 'sha256:' + sha_bytes(args.checkpoint.read_bytes())
    code_hashes = {name: sha_bytes((Path(__file__).parent / name).read_bytes())
                   for name in ('broker.py', 'encoder.py', 'model.py')}
    stop = False

    def requested_stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, requested_stop)
    signal.signal(signal.SIGINT, requested_stop)
    done = set()
    last_activity = time.monotonic()
    atomic(directory / 'broker-ready.json', json.dumps(dict(pid=os.getpid(), mode=args.mode,
        model_version=model_version, encoder_version=ENCODER_VERSION, code_sha256=code_hashes)).encode())
    print(json.dumps(dict(status='ready', directory=str(directory), mode=args.mode)), flush=True)
    while not stop and (not args.max_requests or len(done) < args.max_requests):
        pending = sorted(path for path in directory.glob('request-*.json') if FILE.match(path.name))
        for path in pending:
            number = int(FILE.match(path.name)[1])
            if number in done:
                continue
            action_path = directory / f'action-{number:08d}.json'
            request_bytes = path.read_bytes()
            base = dict(request_id=number, request_file=path.name,
                        request_sha256=sha_bytes(request_bytes), mode=args.mode,
                        model_version=model_version, encoder_version=ENCODER_VERSION,
                        broker_code_sha256=code_hashes, monotonic_seconds=time.monotonic())
            try:
                request = validate(json.loads(request_bytes), number)
                if action_path.exists():
                    raise ValueError('Existing response in this broker session; use a fresh per-game directory')
                value = None
                if model is None:
                    action = max(range(len(request['candidates'])),
                                 key=lambda i: request['candidates'][i]['heuristic_score'])
                else:
                    from encoder import collate
                    with torch.no_grad():
                        logits, values = model(**collate([request], 'cpu'))
                        action, value = int(logits.argmax(dim=1)[0]), float(values[0])
                if not 0 <= action < len(request['candidates']):
                    raise ValueError('Selected candidate outside supplied legal range')
                data = f'{action}\n'.encode('ascii')
                event = dict(base, event='decision_committed', action=action,
                             candidates_count=len(request['candidates']), player=request['player'],
                             day=request['day'], hero=request['hero'], value=value,
                             action_file=action_path.name, response_sha256=sha_bytes(data))
                append_trace(trace, event)
                atomic(action_path, data)
                append_trace(trace, dict(base, event='response_written', action=action,
                                        response_sha256=sha_bytes(data)))
            except (ValueError, KeyError, TypeError, RuntimeError) as error:
                append_trace(trace, dict(base, event='protocol_error', error=str(error)))
                atomic(directory / f'error-{number:08d}.json',
                       json.dumps(dict(request_id=number, error=str(error))).encode())
                print(json.dumps(dict(status='request_error', request_id=number, error=str(error))), flush=True)
            done.add(number)
            last_activity = time.monotonic()
        if args.idle_seconds and time.monotonic() - last_activity > args.idle_seconds:
            break
        if not stop:
            time.sleep(max(1, args.poll_ms) / 1000)
    print(json.dumps(dict(status='stopped', processed=len(done))), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
