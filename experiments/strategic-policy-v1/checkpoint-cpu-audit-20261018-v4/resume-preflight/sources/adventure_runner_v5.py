#!/usr/bin/env python3
"""Isolated full-game runner with immutable evidence and fail-closed outcomes."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

LAB = Path('/root/heroes3-ai-lab')
SHARED = Path('/mnt/g/Heroes3-AI-Lab')
BIN = LAB / 'src/vcmi-adv-build/bin'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--map', default='Maps/adv/adv-arena-01')
    p.add_argument('--red', default='DirectorAI')
    p.add_argument('--blue', default='Nullkiller2')
    p.add_argument('--seed', type=int, default=2026101801)
    p.add_argument('--seconds', type=int, default=180)
    p.add_argument('--tag', default='takeover-v5')
    p.add_argument('--save-file', default='', help='Native .vsgm1; load instead of starting a map')
    p.add_argument('--gdb', action='store_true', help='Capture native failure stacks; never treat debugger exit as engine exit')
    p.add_argument('--agent-dir', default='', help='Exclusive request/response directory for a local strategy policy')
    args = p.parse_args()
    root = LAB / 'workers/adv-runs'
    root.mkdir(parents=True, exist_ok=True)
    w = Path(tempfile.mkdtemp(prefix=f'{args.tag}-{args.seed}-', dir=root))
    for d in ['data/vcmi/Maps/adv', 'data/vcmi/config', 'config', 'cache']:
        (w / d).mkdir(parents=True, exist_ok=True)
    for name in ['Data', 'Mods']:
        (w / 'data/vcmi' / name).symlink_to(LAB / 'data/vcmi' / name)
    for source in (LAB / 'data/vcmi/Maps/adv').glob('*.vmap'):
        shutil.copy2(source, w / 'data/vcmi/Maps/adv' / source.name)
    shutil.copytree(BIN / 'config', w / 'config', dirs_exist_ok=True)
    settings = dict(mods=dict(validation='off'), general=dict(music=0, sound=0, showIntro=False),
                    adventure=dict(enemyMoveTime=0, heroMoveTime=0),
                    server=dict(seed=args.seed), session=dict(onlyai=True))
    for d in [w / 'config', w / 'data/vcmi/config']:
        (d / 'settings.json').write_text(json.dumps(settings))
        (d / 'modSettings.json').write_text(json.dumps(dict(activePreset='adv',
            presets=dict(adv=dict(mods=['core', 'vcmi'], settings={})))) )
        for name in ['persistentStorage.json', 'keyBindingsConfig.json']:
            (d / name).write_text('{}')
    env = dict(os.environ, LD_LIBRARY_PATH=str(BIN), SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy',
               XDG_DATA_HOME=str(w / 'data'), XDG_CONFIG_HOME=str(w), XDG_CACHE_HOME=str(w / 'cache'),
               LAB_ADV_AI_0=args.red, LAB_ADV_AI_1=args.blue, LAB_ADV_TRACE=str(w / 'strategy-trace.jsonl'),
               LAB_ADV_DECISIONS=str(w / 'strategy-decisions.jsonl'))
    if args.agent_dir:
        agent_dir = Path(args.agent_dir).resolve()
        agent_dir.mkdir(parents=True, exist_ok=True)
        if list(agent_dir.glob('request-*.json')) or list(agent_dir.glob('action-*.json')):
            raise ValueError('Local policy directory already contains an earlier episode')
        if args.red == args.blue == 'DirectorAI':
            raise ValueError('Two DirectorAI players require distinct protocol directories')
        env['LAB_ADV_AGENT_DIR'] = str(agent_dir)
    inputs = [BIN / n for n in ['vcmiclient', 'vcmiserver', 'libvcmi.so']]
    inputs += list((LAB / 'src/vcmi-adv/AI/DirectorAI').glob('*.cpp'))
    inputs += list((LAB / 'src/vcmi-adv/AI/DirectorAI').glob('*.h'))
    map_file = w / 'data/vcmi' / (args.map + '.vmap')
    inputs += [map_file, Path(__file__).resolve()]
    if args.save_file:
        original_save = Path(args.save_file).resolve()
        head = original_save.read_bytes()[:15]
        if original_save.suffix.lower() != '.vsgm1' or head[:4] != b'VCMI' or head[8:15] != b'VCMISVG':
            raise ValueError('Invalid native VCMI save header')
        (w / 'data/vcmi/Saves').mkdir()
        copy_save = w / 'data/vcmi/Saves/takeover-resume-snapshot.vsgm1'
        shutil.copy2(original_save, copy_save)
        inputs += [original_save, copy_save]
    hashes = {str(f): sha(f) for f in inputs}
    snapshot = w / 'source-snapshot'
    snapshot.mkdir()
    for f in inputs:
        if f.suffix in ['.h', '.cpp', '.py']:
            shutil.copy2(f, snapshot / f.name)
    (w / 'plan.json').write_text(json.dumps(dict(config=vars(args), hashes=hashes), indent=2))
    print('RUN_DIR=' + str(w), flush=True)
    lock_path = LAB / 'evaluations/.pool-lock'
    with lock_path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        start = time.monotonic()
        with (w / 'client.log').open('w') as log:
            start_arg = ['--testsave', 'Saves/takeover-resume-snapshot'] if args.save_file else ['--testmap', args.map]
            command = [str(BIN / 'vcmiclient'), '--headless'] + start_arg + [
                '--nointro', '--disable-video', '--savefrequency', '1']
            if args.gdb:
                command = ['gdb', '-q', '-batch', '-ex', 'set pagination off', '-ex', 'run',
                           '-ex', 'thread apply all bt 20', '-ex', 'p $_exitcode',
                           '-ex', 'p $_exitsignal', '--args'] + command
            proc = subprocess.Popen(command, cwd=w, env=env,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            timed_out = False
            interrupted = False
            def stop_run(signum, frame):
                raise InterruptedError('Runner received termination signal')
            old_term = signal.signal(signal.SIGTERM, stop_run)
            old_int = signal.signal(signal.SIGINT, stop_run)
            try:
                code = proc.wait(timeout=args.seconds)
            except (subprocess.TimeoutExpired, InterruptedError) as error:
                timed_out = isinstance(error, subprocess.TimeoutExpired)
                interrupted = isinstance(error, InterruptedError)
            finally:
                # This child owns a separate session. Always clean its group before
                # releasing the pool lock, including outer trainer termination.
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    pass
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                code = proc.wait()
                signal.signal(signal.SIGTERM, old_term)
                signal.signal(signal.SIGINT, old_int)
        elapsed = time.monotonic() - start
    log = (w / 'client.log').read_text(errors='replace')
    process_exit = code
    if args.gdb:
        code = 0 if 'exited normally]' in log and not timed_out else None
    assignment = dict(re.findall(r'Player ([a-z]+) will be lead by ([A-Za-z0-9]+)', log))
    wins = re.findall(r'AIGateway: Player (\d+) \((\w+)\) won', log)
    losses = re.findall(r'AIGateway: Player (\d+) \((\w+)\) lost', log)
    winner = wins[-1][1] if wins else None
    direct_wins = re.findall(r'DirectorAI: native gameOver player=(\w+) victory=1 loss=0', log)
    if direct_wins:
        winner = direct_wins[-1]
    if winner is None and losses:
        winner = {'red': 'blue', 'blue': 'red'}.get(losses[-1][1])
    turns = re.findall(r'Turn nr (\d+)', log)
    load_markers = {s: s in log for s in ['Preparing to start loaded game',
                   'Game has been successfully loaded!', 'Game loaded, initialize interfaces.']}
    load_verified = all(load_markers.values()) if args.save_file else None
    moves = re.findall(r'DirectorAI: step finished result=(\d+) points_left=(\d+) from (\([^)]*\)) to (\([^)]*\))', log)
    changed = [m for m in moves if m[2] != m[3] and int(m[0]) != 0]
    unchanged_inputs = all(sha(Path(f)) == digest for f, digest in hashes.items())
    crashed = bool(re.search(r'Disaster happened|SIGSEGV|SIGABRT|dumped core', log)) or (code is not None and code < 0 and not timed_out)
    complete = (code == 0 and not timed_out and not interrupted and not crashed and
                assignment == dict(red=args.red, blue=args.blue) and
                'All players have ended the game.' in log and winner is not None and unchanged_inputs and
                (not args.save_file or load_verified) and 'external policy failed' not in log)
    result = dict(schema='adventure-run-v5', run_dir=str(w), config=vars(args), engine_exit=code,
                  timed_out=timed_out, interrupted=interrupted, crashed=crashed, completed=complete, winner=winner,
                  wrapper_exit=process_exit,
                  actual_ai=assignment, turns=int(turns[-1]) if turns else None,
                  moves_requested=log.count('DirectorAI: step hero'), move_replies=len(moves),
                  changed_tile_replies=len(changed),
                  failed_move_replies=sum(int(m[0]) == 0 for m in moves),
                  inputs_unchanged=unchanged_inputs, log_sha256=sha(w / 'client.log'),
                  native_load_verified=load_verified, load_markers=load_markers if args.save_file else None,
                  wall_seconds=elapsed, limitations=(
                      'External local target policy; economics scripted; effectiveness requires separate evaluation.'
                      if args.agent_dir else 'Scripted strategy; delegated native battles; no learned strategic model.'))
    trace = w / 'strategy-trace.jsonl'
    if trace.exists():
        result['strategy_trace_sha256'] = sha(trace)
        result['strategy_trace_records'] = sum(1 for _ in trace.open())
    decisions = w / 'strategy-decisions.jsonl'
    if decisions.exists():
        result['strategy_decisions_sha256'] = sha(decisions)
        result['strategy_decision_records'] = sum(1 for _ in decisions.open())
    result['save_files'] = [dict(path=str(f), bytes=f.stat().st_size, sha256=sha(f))
                            for f in w.rglob('*.vsgm1')]
    (w / 'result.json').write_text(json.dumps(result, indent=2))
    reports = SHARED / 'experiments/adventure-takeover-v5/runs'
    reports.mkdir(parents=True, exist_ok=True)
    (reports / (w.name + '.json')).write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
