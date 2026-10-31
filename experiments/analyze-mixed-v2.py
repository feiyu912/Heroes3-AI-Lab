"""Decompose the 48-scenario development result by role, scenario and seed.

Reads only already-produced evaluation reports. No game is launched.
"""
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'expert-mixed-b64-run-v2'
CANDIDATES = ['b64-baseline', 'mixed-16', 'mixed-32']
OPPONENTS = ['BattleAI', 'MMAI_MODEL']


def load(candidate, opponent):
    return json.loads((OUT / f'{candidate}-{opponent}-development.json').read_text(encoding='utf-8-sig'))


def index(report):
    return {(row['scenario'], row['role'], row['seed']): row for row in report['battles']}


def main():
    table = {}
    for opponent in OPPONENTS:
        for candidate in CANDIDATES:
            table[(candidate, opponent)] = index(load(candidate, opponent))
    summary = {}
    for (candidate, opponent), rows in table.items():
        by_role = defaultdict(lambda: [0, 0])
        for (scenario, role, seed), row in rows.items():
            by_role[role][0] += int(row['success'])
            by_role[role][1] += 1
        summary[f'{candidate}|{opponent}'] = {role: dict(wins=v[0], games=v[1], rate=round(v[0] / v[1], 4))
                                              for role, v in sorted(by_role.items())}
    # per-scenario delta against the B64 baseline
    delta = {}
    for opponent in OPPONENTS:
        base = table[('b64-baseline', opponent)]
        for candidate in CANDIDATES[1:]:
            cur = table[(candidate, opponent)]
            changed = []
            for key in sorted(base):
                if base[key]['success'] != cur[key]['success']:
                    changed.append(dict(scenario=key[0], role=key[1], seed=key[2],
                                        baseline=bool(base[key]['success']), candidate=bool(cur[key]['success'])))
            lost = [c for c in changed if c['baseline'] and not c['candidate']]
            won = [c for c in changed if not c['baseline'] and c['candidate']]
            delta[f'{candidate}|{opponent}'] = dict(net=len(won) - len(lost), gained=len(won), lost=len(lost),
                                                    flipped=changed)
    # scenarios the baseline loses, per opponent
    hard = {}
    for opponent in OPPONENTS:
        base = table[('b64-baseline', opponent)]
        losses = defaultdict(lambda: 0)
        for (scenario, role, seed), row in base.items():
            if not row['success']:
                losses[(scenario, role)] += 1
        hard[opponent] = [dict(scenario=s, role=r, seeds_lost=n) for (s, r), n in sorted(losses.items())]
    result = dict(source='expert-mixed-b64-run-v2/*-development.json', role_split=summary,
                  delta_vs_baseline=delta, baseline_losses=hard,
                  note='Development set only; used for method decisions, never as independent confirmation.')
    (OUT / 'development-analysis.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    for key, value in summary.items():
        print(key, value)
    for key, value in delta.items():
        print(key, 'net', value['net'], 'gained', value['gained'], 'lost', value['lost'])
    for opponent in OPPONENTS:
        print(opponent, 'baseline losses:', len(hard[opponent]), hard[opponent][:12])


if __name__ == '__main__':
    main()
