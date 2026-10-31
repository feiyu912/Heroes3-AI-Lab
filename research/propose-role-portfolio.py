"""Explore frozen per-role checkpoint combinations on existing validation only.

The two role networks never interact during inference. Concatenated matched-role
results predict a portfolio's validation score exactly; real games are still
required before adding the derived candidate to final model selection.
"""
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np
from lab_io import atomic_json
from goal_selection import rank as goal_rank, score as goal_score


def main():
    root = Path(__file__).resolve().parent
    rows = [row for row in json.loads((root / 'goal-v5-validation.json').read_text())
            if row['policy'] == 'recovered' and row.get('finetuning_mode') != 'derived']
    cached = {}
    canonical = {}
    for prefix in ['', 'development_']:
        for opponent_prefix in ['', 'upstream_']:
            key = prefix + opponent_prefix + 'validation_report'
            for row in rows:
                records = json.loads(Path(row[key]).read_text())['battles']
                conditions = {(record['scenario'], record['role'], record['seed']) for record in records}
                assert len(conditions) == len(records)
                assert all(record['terminated'] and not record['truncated'] and
                           record['invalid_actions'] == 0 for record in records)
                if key not in canonical:
                    canonical[key] = conditions
                assert canonical[key] == conditions
                for role in ['attacker', 'defender']:
                    subset = [record for record in records if record['role'] == role]
                    case_names = sorted({record['scenario'] for record in subset})
                    case_means = np.asarray([np.mean([record['success'] for record in subset
                                                     if record['scenario'] == case]) for case in case_names])
                    rng = np.random.default_rng(2026101520)
                    draws = rng.integers(0, len(case_names), (10000, len(case_names)))
                    lost=np.mean([sum(record['terminal_outcome']['casualties'][str(int(role=='defender'))].values()) for record in subset])
                    cached[row['name'], key, role] = (case_means.mean(), case_means[draws].mean(1),lost)

    def statistics(attacker, defender):
        rates = {}
        lower = {}
        for prefix in ['', 'development_']:
            for opponent in ['', 'upstream_']:
                key = prefix + opponent + 'validation_report'
                a = cached[attacker['name'], key, 'attacker']
                d = cached[defender['name'], key, 'defender']
                rates[prefix + opponent + 'win_rate'] = float((a[0] + d[0]) / 2)
                if opponent:
                    lower[prefix + 'author_lower'] = float(np.quantile((a[1] + d[1]) / 2, .025))
        loss=(cached[attacker['name'],'development_validation_report','attacker'][2]+
              cached[defender['name'],'development_validation_report','defender'][2])/2
        proxy=dict(validation=dict(win_rate=rates['win_rate']),
            upstream_validation=dict(win_rate=rates['upstream_win_rate']),
            development_validation=dict(win_rate=rates['development_win_rate'],mean_permanent_units_lost=loss),
            development_upstream_validation=dict(win_rate=rates['development_upstream_win_rate']))
        score=goal_rank(proxy,dict(development_author_cluster95_lower=lower['development_author_lower']))
        return dict(attacker=attacker['name'], defender=defender['name'], score=score,
                    predicted_validation_rates=rates, cluster95_lower=lower)

    combinations = [statistics(a, d) for a, d in itertools.product(rows, repeat=2)]
    combinations.sort(key=lambda result: result['score'], reverse=True)
    singles = [statistics(row, row) for row in rows]
    for row,single in zip(rows,singles):
        np.testing.assert_allclose(single['score'],goal_score(row),atol=1e-11,rtol=0)
    best_single = max(singles, key=lambda result: result['score'])
    best = combinations[0]
    names = {row['name']: row for row in rows}
    sources = {}
    for role in ['attacker', 'defender']:
        checkpoint = Path(names[best[role]]['checkpoint'])
        sources[role] = dict(checkpoint=str(checkpoint),
                            sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest())
    result = dict(final_holdout_read=False, source_models=len(rows),
                  scope='Existing old/development validation; no new model weights or win claims',
                  best_single=best_single, best_portfolio=best, sources=sources,
                  promising=best['score'] > best_single['score'], top_combinations=combinations[:10],
                  next_gate='If promising, materialize the two frozen role networks and verify in real native-opponent games before selection. Fresh final test remains mandatory.')
    atomic_json(root / 'role-portfolio-proposal.json', result)
    print(json.dumps({key: result[key] for key in ['promising', 'best_single', 'best_portfolio']}, indent=2))


if __name__ == '__main__':
    main()
