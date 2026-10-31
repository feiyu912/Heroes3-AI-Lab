import argparse
import importlib.util
import json
from pathlib import Path
import os
import resource
import time
import numpy as np

latencies = []

spec = importlib.util.spec_from_file_location('battle_smoke', Path(__file__).with_name('battle-smoke.py'))
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

parser = argparse.ArgumentParser()
parser.add_argument('--control', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--ready', required=True)
parser.add_argument('--seed', type=int, default=20261013)
args = parser.parse_args()
boot_start = time.monotonic()
env = smoke.VcmiEnv(mapname='lab/smoke.vmap', seed=args.seed, role='attacker',
                    opponent='BattleAI', max_steps=200, render_mode='ansi',
                    random_heroes=0, random_obstacles=0, town_chance=0,
                    warmachine_chance=0, random_armies=False, mana_min=0, mana_max=0,
                    user_timeout=30, vcmi_timeout=30, boot_timeout=30,
                    vcmi_loglevel_global='error', vcmi_loglevel_ai='error')
boot_seconds = time.monotonic() - boot_start


def episode():
    reset_start = time.monotonic()
    obs, _ = env.reset()
    reset_time = time.monotonic() - reset_start
    steps = 0
    step_time = decision_time = 0.0
    term = trunc = False
    while not (term or trunc):
        decision_start = time.monotonic()
        action = smoke.choose_action(obs)
        decision_time += time.monotonic() - decision_start
        step_start = time.monotonic()
        obs, reward, term, trunc, info = env.step(action)
        latency = time.monotonic() - step_start
        step_time += latency
        latencies.append(latency)
        steps += 1
    assert term and not trunc
    outcome = obs['terminal_outcome']
    assert outcome['result_type'] == 0 and outcome['winner'] == 0
    assert sum(outcome['casualties'][1].values()) == 10
    assert sum(outcome['initial_armies'][0].values()) == 20
    return steps, reset_time, step_time, decision_time


episode()  # warm up before synchronized measurement
latencies.clear()
Path(args.ready).write_text(json.dumps({'pid': os.getpid(), 'boot_seconds': boot_seconds,
                                     'data_home': os.environ['XDG_DATA_HOME']}))
control = Path(args.control)
ready_deadline = time.monotonic() + 30
while not control.exists():
    assert time.monotonic() < ready_deadline, 'Supervisor did not start measurement'
    time.sleep(0.01)
schedule = json.loads(control.read_text())
while time.monotonic() < schedule['start']:
    time.sleep(0.001)
cpu_before = resource.getrusage(resource.RUSAGE_SELF)
started = time.monotonic()
steps = episodes = 0
reset_seconds = step_seconds = decision_seconds = 0.0
while time.monotonic() < schedule['deadline']:
    result = episode()
    steps += result[0]
    reset_seconds += result[1]
    step_seconds += result[2]
    decision_seconds += result[3]
    episodes += 1
ended = time.monotonic()
usage = resource.getrusage(resource.RUSAGE_SELF)
result = {'pid': os.getpid(), 'episodes': episodes, 'steps': steps,
          'started': started, 'ended': ended, 'boot_seconds': boot_seconds,
          'reset_seconds': reset_seconds, 'step_seconds': step_seconds,
          'decision_seconds': decision_seconds,
          'cpu_seconds': usage.ru_utime + usage.ru_stime - cpu_before.ru_utime - cpu_before.ru_stime,
          'peak_rss_mib': usage.ru_maxrss / 1024,
          'terminal_checks_passed': True, 'worker_data_home': os.environ['XDG_DATA_HOME']}
result['step_latency_ms_percentiles'] = dict(zip(['p50', 'p90', 'p95', 'p99'],
                                                np.percentile(latencies, [50, 90, 95, 99]) * 1000))
Path(args.output).write_text(json.dumps(result, indent=2))
env.close()
