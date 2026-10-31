#!/usr/bin/env python3
"""Frozen development-only multi-map, role-swapped full-game comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parent / 'adventure_runner_v5.py'
BIN = Path('/root/heroes3-ai-lab/src/vcmi-adv-build/bin')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    inputs = [RUNNER, Path(__file__).resolve(), BIN / 'vcmiclient', BIN / 'vcmiserver', BIN / 'libvcmi.so']
    inputs += list((Path('/root/heroes3-ai-lab/src/vcmi-adv/AI/DirectorAI')).glob('*.cpp'))
    inputs += list((Path('/root/heroes3-ai-lab/src/vcmi-adv/AI/DirectorAI')).glob('*.h'))
    maps = ['takeover-open-36-v1', 'takeover-detour-36-v1', 'takeover-economy-36-v1']
    for m in maps:
        inputs.append(Path('/root/heroes3-ai-lab/data/vcmi/Maps/adv') / (m + '.vmap'))
    jobs = []
    for m in maps:
        for seed in [2026101811, 2026101812]:
            for red, blue in [('DirectorAI', 'Nullkiller2'), ('Nullkiller2', 'DirectorAI'),
                              ('Nullkiller2', 'Nullkiller2')]:
                jobs.append(dict(map='Maps/adv/' + m, seed=seed, red=red, blue=blue))
    hashes = {str(f): sha(f) for f in inputs}
    plan = dict(schema='adventure-development-v1', jobs=jobs, hashes=hashes,
                held_out=False, purpose='Engineering/heuristic baseline, not learned-policy performance confirmation.')
    (a.out / 'plan.json').write_text(json.dumps(plan, indent=2))
    results = []
    start = time.monotonic()
    for i, job in enumerate(jobs):
        assert all(sha(Path(f)) == h for f, h in hashes.items()), 'Protocol changed during batch'
        command = [sys.executable, str(RUNNER), '--map', job['map'], '--red', job['red'],
                   '--blue', job['blue'], '--seed', str(job['seed']), '--seconds', '90',
                   '--tag', a.out.name + '-' + str(i)]
        proc = subprocess.run(command, capture_output=True, text=True)
        (a.out / f'{i:02d}.stdout.txt').write_text(proc.stdout)
        (a.out / f'{i:02d}.stderr.txt').write_text(proc.stderr)
        summaries = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith('{')]
        result = summaries[-1] if summaries else dict(completed=False, error='Missing runner result')
        result.update(job_index=i, runner_exit=proc.returncode)
        results.append(result)
        report = dict(plan_sha256=sha(a.out / 'plan.json'), completed_jobs=len(results),
                      total_jobs=len(jobs), all_jobs_finished=len(results) == len(jobs),
                      results=results, wall_seconds=time.monotonic() - start)
        report['all_games_valid'] = all(r.get('completed') and r['runner_exit'] == 0 for r in results)
        (a.out / 'results.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(dict(job=i, valid=result.get('completed'), winner=result.get('winner'),
                             turns=result.get('turns'), steps=result.get('changed_tile_replies'))), flush=True)
    return 0 if report['all_games_valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
