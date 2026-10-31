"""Final development-set report: rates, scenario-clustered intervals, loss taxonomy, distance to target."""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent / 'expert-mixed-b64-run-v2'
CANDIDATES = ['public-original', 'b64-baseline', 'mixed-16', 'mixed-32']
OPPONENTS = ['BattleAI', 'MMAI_MODEL']
TARGET = 0.95
RNG = np.random.default_rng(20261017)


def load(name):
    path = OUT / f'{name}-development.json'
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else None


def cluster_ci(rows, rounds=4000):
    """Bootstrap over scenarios, keeping all seeds/roles of a scenario together."""
    by_scenario = defaultdict(list)
    for row in rows:
        by_scenario[row['scenario']].append(int(row['success']))
    keys = sorted(by_scenario)
    means = []
    for _ in range(rounds):
        pick = RNG.choice(len(keys), len(keys), replace=True)
        sample = [value for index in pick for value in by_scenario[keys[index]]]
        means.append(np.mean(sample))
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def main():
    report = {}
    cells = {}
    for opponent in OPPONENTS:
        for candidate in CANDIDATES:
            data = load(f'{candidate}-{opponent}')
            if data is None:
                continue
            rows = data['battles']
            summary = data['summary'][0]
            role = defaultdict(lambda: [0, 0])
            for row in rows:
                role[row['role']][0] += int(row['success'])
                role[row['role']][1] += 1
            entry = dict(
                wins=summary['wins'], games=summary['battles'],
                rate=summary['wins'] / summary['battles'],
                wilson95=[round(x, 4) for x in summary['wilson95']],
                scenario_cluster95=[round(x, 4) for x in cluster_ci(rows)],
                role={k: dict(wins=v[0], games=v[1], rate=round(v[0] / v[1], 4)) for k, v in sorted(role.items())},
                truncated=summary['truncated'], invalid_actions=summary['invalid_actions'],
                non_normal_terminations=summary['non_normal_terminations'],
                mean_units_lost=round(summary['mean_permanent_units_lost'], 2))
            if opponent == 'BattleAI':
                needed = int(np.ceil(TARGET * summary['battles']))
                entry['wins_needed_for_95'] = needed
                entry['wins_short'] = needed - summary['wins']
            report[f'{candidate}|{opponent}'] = entry
            cells[(candidate, opponent)] = {(r['scenario'], r['role'], r['seed']): bool(r['success']) for r in rows}

    taxonomy = {}
    base = cells.get(('b64-baseline', 'BattleAI'))
    pub = cells.get(('public-original', 'BattleAI'))
    if base and pub:
        both_lose = [k for k in base if not base[k] and not pub[k]]
        pub_only = [k for k in base if not base[k] and pub[k]]
        taxonomy = dict(
            b64_losses=len([k for k in base if not base[k]]),
            lost_by_public_too=len(both_lose),
            public_wins_b64_loses=len(pub_only),
            both_lose_cells=sorted({(k[0], k[1]) for k in both_lose}),
            public_only_cells=sorted({(k[0], k[1]) for k in pub_only}),
            ceiling_if_public_imitated_perfectly=dict(
                wins=172 + len(pub_only), games=192, rate=round((172 + len(pub_only)) / 192, 4)))
    result = dict(source='expert-mixed-b64-run-v2/*-development.json', target=TARGET,
                  development_scenarios=list(range(192, 240)), seeds=2, roles=2,
                  games_per_cell=192, models=report, loss_taxonomy=taxonomy,
                  note=('Development set. Used to choose the next method, never as independent confirmation. '
                        'Scenario-clustered intervals resample whole scenarios, not individual games.'))
    (OUT / 'final-development-report.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')

    print(f"{'model':16s} {'opponent':12s} {'wins':>9s} {'rate':>7s} {'cluster95':>16s} {'att':>6s} {'def':>6s}  flags")
    for key, e in report.items():
        model, opponent = key.split('|')
        flags = []
        if e['truncated']:
            flags.append(f"trunc={e['truncated']}")
        if e['invalid_actions']:
            flags.append(f"invalid={e['invalid_actions']}")
        print(f"{model:16s} {opponent:12s} {e['wins']:4d}/{e['games']:<4d} {e['rate']*100:6.2f}% "
              f"{e['scenario_cluster95'][0]*100:6.2f}-{e['scenario_cluster95'][1]*100:6.2f}% "
              f"{e['role']['attacker']['rate']*100:5.2f}% {e['role']['defender']['rate']*100:5.2f}%  {','.join(flags) or 'clean'}")
    print()
    print('BattleAI distance to 95%:', {k: v['wins_short'] for k, v in report.items() if k.endswith('BattleAI')})
    print('loss taxonomy:', json.dumps(taxonomy, ensure_ascii=False))


if __name__ == '__main__':
    main()
