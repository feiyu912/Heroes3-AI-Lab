#!/usr/bin/env python3
"""events-v2 batch pilot driver.

Runs N single-episode processes (one VCMI instance per process, hard limit)
SERIALLY, each taking the shared global pool lock. Records a manifest with
per-episode status. No parallel game pools: the shared 24-worker budget is
reserved for training; this is a small native verification campaign.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tactic', required=True)
    parser.add_argument('--policies', nargs='+', required=True)
    parser.add_argument('--roles', nargs='+', default=['attacker', 'defender'])
    parser.add_argument('--scenarios', nargs='+', type=int, required=True)
    parser.add_argument('--seeds', nargs='+', type=int, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--checkpoint', default='')
    parser.add_argument('--runner', choices=['v2', 'v3'], default='v3')
    args = parser.parse_args()

    outdir = HERE / 'runs' / args.tag
    outdir.mkdir(parents=True, exist_ok=True)
    manifest_path = outdir / 'manifest.json'
    manifest = []
    jobs = []
    for sc in args.scenarios:
        for role in args.roles:
            for policy in args.policies:
                for seed in args.seeds:
                    name = f'{policy}-{args.tactic}-{sc:02d}-{role}-s{seed}'
                    jobs.append((name, sc, role, policy, seed))

    runner = 'run_episode_events_v3.py' if args.runner == 'v3' else 'run_episode_events.py'
    scenario_file = 'scenarios-v3.json' if args.runner == 'v3' else 'scenarios.json'
    for i, (name, sc, role, policy, seed) in enumerate(jobs):
        out = outdir / f'{name}.json'
        entry = dict(job=name, scenario=sc, role=role, policy=policy, seed=seed, status='pending')
        if out.exists():
            rec = json.loads(out.read_text())
            entry['status'] = 'completed' if rec.get('completed') else 'failed-previous'
            manifest.append(entry)
            print(f'[{i+1}/{len(jobs)}] skip existing {name}: {entry["status"]}', flush=True)
            continue
        cmd = ['bash', str(HERE / 'run-events-lab.sh'), str(HERE / runner),
               '--scenario', str(sc), '--role', role, '--seed', str(seed),
               '--policy', policy, '--checkpoint', args.checkpoint or 'none',
               '--scenario-file', scenario_file,
               '--output', str(out)]
        started = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        entry['seconds'] = round(time.time() - started, 1)
        if out.exists() and json.loads(out.read_text()).get('completed'):
            entry['status'] = 'completed'
        else:
            entry['status'] = 'failed'
            entry['stderr_tail'] = proc.stderr[-2000:]
            entry['stdout_tail'] = proc.stdout[-2000:]
        manifest.append(entry)
        print(f'[{i+1}/{len(jobs)}] {name}: {entry["status"]} ({entry.get("seconds")}s)', flush=True)
        manifest_path.write_text(json.dumps(manifest, indent=1))
        if entry['status'] == 'failed':
            print('FAILED job; stopping pilot for inspection', flush=True)
            break
    ok = sum(1 for e in manifest if e['status'] == 'completed')
    print(f'done: {ok}/{len(jobs)} completed', flush=True)


if __name__ == '__main__':
    main()
