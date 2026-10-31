"""Frozen CPU argmax evaluation; native outcomes only, no optimizer or test split."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False))
    temp.replace(path)


def verify_native_consumption(agent_dir, native, expected_sha):
    """Broker IO alone does not establish that native consumed the same actions."""
    ready = json.loads((agent_dir / 'broker-ready.json').read_text())
    if ready.get('model_version') != 'sha256:' + expected_sha:
        raise ValueError('Broker loaded an unexpected checkpoint')
    committed = [json.loads(line) for line in (agent_dir / 'broker-trace.jsonl').read_text().splitlines()
                 if json.loads(line).get('event') == 'decision_committed']
    decisions = [json.loads(line) for line in
                 (Path(native['run_dir']) / 'strategy-decisions.jsonl').read_text().splitlines()]
    if not committed or len(committed) != len(decisions):
        raise ValueError('Broker/native decision counts differ or are empty')
    for number, (event, decision) in enumerate(zip(committed, decisions), 1):
        request = json.loads((agent_dir / event['request_file']).read_text())
        action = event['action']
        candidate = request['candidates'][action]
        if not (event['request_id'] == request['request_id'] == number and
                decision['selected_candidate'] == action and
                all(decision[k] == request[k] for k in ('player', 'day', 'hero', 'from')) and
                decision['destination'] == candidate['position'] and decision['step'] == candidate['next']):
            raise ValueError(f'Native consumption mismatch at request {number}')
    return len(decisions)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, default=HERE / 'checkpoints/prior-initial-v2.pt')
    parser.add_argument('--seeds', type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.seeds <= 100:
        parser.error('--seeds must be between 1 and 100 (unique native seed schedule)')
    args.out.mkdir(parents=True, exist_ok=False)
    models = {'baseline': args.baseline.resolve(), 'candidate': args.candidate.resolve()}
    inputs = list(models.values()) + [HERE / name for name in
        ['evaluate_pairs.py', 'smoke_game.py', 'broker.py', 'encoder.py', 'model.py']]
    inputs += [HERE.parent / 'adventure_runner_v5.py']
    runtime = Path('/root/heroes3-ai-lab/src/vcmi-adv-build/bin')
    inputs += [runtime / name for name in ['vcmiclient', 'vcmiserver', 'libvcmi.so']]
    inputs += [path for path in (runtime / 'config').rglob('*') if path.is_file()]
    director = Path('/root/heroes3-ai-lab/src/vcmi-adv/AI/DirectorAI')
    inputs += list(director.glob('*.cpp')) + list(director.glob('*.h'))
    maps = ['takeover-v2-dev-01-river', 'takeover-v2-dev-02-reserves']
    inputs += [Path('/root/heroes3-ai-lab/data/vcmi/Maps/adv') / (m + '.vmap') for m in maps]
    hashes = {str(p): sha(p) for p in inputs}
    jobs = [dict(map='Maps/adv/' + m, opponent=opponent, role=role,
                 seed=2026102800 + 10000 * mi + 100 * oi + si)
            for mi, m in enumerate(maps) for oi, opponent in enumerate(['EmptyAI', 'Nullkiller2'])
            for role in ['red', 'blue'] for si in range(args.seeds)]
    plan = dict(schema='strategic-independent-paired-development-v1', models={k: str(v) for k, v in models.items()},
                hashes=hashes, jobs=jobs, selection='Frozen CPU argmax, no training.',
                test_split_touched=False, pair_unit='same map, role, opponent, native seed',
                limitations='Small fixed development set; maps/roles are clustered; no final-test claim.')
    plan['run_order'] = 'Alternate baseline/candidate first by paired job index; no concurrent simulations.'
    atomic_json(args.out / 'plan.json', plan)
    snapshot = args.out / 'sources'
    snapshot.mkdir()
    for index, path in enumerate(inputs):
        if path.suffix in ('.py', '.cpp', '.h', '.json'):
            shutil.copy2(path, snapshot / f'{index:03d}-{path.name}')
    rows = []
    report = dict(status='running', rows=rows, independent_of_optimizer=True, test_split_touched=False)
    atomic_json(args.out / 'results.json', report)
    try:
      for ji, job in enumerate(jobs):
        order = ['baseline', 'candidate'] if ji % 2 == 0 else ['candidate', 'baseline']
        for name in order:
            checkpoint = models[name]
            if not all(sha(Path(p)) == h for p, h in hashes.items()):
                raise RuntimeError('Frozen evaluation inputs changed')
            command = [sys.executable, str(HERE / 'smoke_game.py'), '--mode', 'policy',
                       '--checkpoint', str(checkpoint), '--map', job['map'], '--seed', str(job['seed']),
                       '--seconds', '90', '--tag', f'paired-{args.out.name}-{ji}-{name}',
                       '--red', 'DirectorAI' if job['role'] == 'red' else job['opponent'],
                       '--blue', 'DirectorAI' if job['role'] == 'blue' else job['opponent']]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            (args.out / f'{ji}-{name}.log').write_text(result.stdout)
            match = re.search(r'^AGENT_DIR=(.+)$', result.stdout, re.MULTILINE)
            summary = json.loads((Path(match[1].strip()) / 'smoke-result.json').read_text()) if match else {}
            native = summary.get('native_result') or {}
            assigned = dict(red='DirectorAI' if job['role'] == 'red' else job['opponent'],
                            blue='DirectorAI' if job['role'] == 'blue' else job['opponent'])
            valid = bool(result.returncode == 0 and summary.get('passed') and native.get('completed') and
                         native.get('inputs_unchanged') and native.get('actual_ai') == assigned and
                         native.get('winner') in ('red', 'blue'))
            consumption, verification_error = None, None
            if valid:
                try:
                    consumption = verify_native_consumption(Path(match[1].strip()), native, hashes[str(checkpoint)])
                except Exception as error:
                    verification_error, valid = repr(error), False
            if not all(sha(Path(p)) == h for p, h in hashes.items()):
                verification_error, valid = 'Frozen evaluation inputs changed during game', False
            row = dict(job=job, model=name, valid=bool(valid),
                       win=native.get('winner') == job['role'] if valid else None,
                       native=native, agent_dir=match[1].strip() if match else None,
                       native_consumption_verified=consumption is not None,
                       native_decisions_verified=consumption, verification_error=verification_error)
            rows.append(row)
            atomic_json(args.out / 'results.json', report)
            print(json.dumps(dict(job=ji, model=name, valid=bool(valid), win=row['win'])), flush=True)
            if not valid:
                raise RuntimeError('Invalid evaluation game; stop and diagnose, no loss imputation')
    except BaseException as error:
        report.update(status='failed', error=repr(error), scores_certified=False)
        atomic_json(args.out / 'results.json', report)
        raise
    pairs = []
    for index, job in enumerate(jobs):
        pair = {row['model']: row for row in rows[index * 2:index * 2 + 2]}
        pairs.append(dict(job=job, baseline_win=pair['baseline']['win'], candidate_win=pair['candidate']['win'],
                          win_delta=int(pair['candidate']['win']) - int(pair['baseline']['win'])))
    report = dict(status='completed', independent_of_optimizer=True, test_split_touched=False,
                  rows=rows, pairs=pairs, net_win_delta=sum(p['win_delta'] for p in pairs),
                  counts={name: dict(games=sum(r['model'] == name for r in rows),
                                    wins=sum(r['model'] == name and r['win'] for r in rows)) for name in models},
                  limitations=plan['limitations'])
    report['discordant_pairs'] = dict(candidate_only_wins=sum(p['win_delta'] == 1 for p in pairs),
                                      baseline_only_wins=sum(p['win_delta'] == -1 for p in pairs))
    report['by_opponent_role'] = {f'{opponent}/{role}': {
        name: dict(games=sum(r['model'] == name and r['job']['opponent'] == opponent and r['job']['role'] == role for r in rows),
                   wins=sum(r['model'] == name and r['job']['opponent'] == opponent and r['job']['role'] == role and r['win'] for r in rows))
        for name in models} for opponent in ('EmptyAI', 'Nullkiller2') for role in ('red', 'blue')}
    atomic_json(args.out / 'results.json', report)


if __name__ == '__main__':
    main()
