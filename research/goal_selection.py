"""Select progress toward 95% BattleAI and demonstrated superiority to MMAI.

The final benchmark uses equal armies. Use the diverse mirror development set
for primary progress; old unequal-army stress cases are diagnostic tie-breakers.
Independent final testing and its success thresholds remain unchanged.
"""
import json
from pathlib import Path
import numpy as np


def rank(row,metrics):
    battle=row['development_validation']['win_rate']
    author=row['development_upstream_validation']['win_rate']
    lower=metrics['development_author_cluster95_lower']
    met=battle>=.95 and lower>.5
    progress=min(battle/.95,lower/.5)
    casualties=row['development_validation']['mean_permanent_units_lost']
    values=(int(met),battle if met else progress,battle,lower,author,
            row['validation']['win_rate']+row['upstream_validation']['win_rate'],
            -casualties if casualties is not None else -float('inf'))
    return tuple(round(float(value),12) for value in values)


def score(row):
    if row.get('goal_selection_metrics',{}).get('rule_version')!=2:
        if 'goal_selection_metrics' in row:
            row.setdefault('prior_goal_selection_metrics',row['goal_selection_metrics'])
        bounds={}
        for prefix in ['', 'development_']:
            path=Path(row[prefix+'upstream_validation_report'])
            records=json.loads(path.read_text())['battles']
            cases=sorted({r['scenario'] for r in records})
            means=np.asarray([np.mean([r['success'] for r in records if r['scenario']==case]) for case in cases])
            rng=np.random.default_rng(2026101520)
            samples=means[rng.integers(0,len(means),(10000,len(means)))].mean(1)
            bounds[prefix+'author_cluster95_lower']=float(np.quantile(samples,.025))
        normalized=[row['development_validation']['win_rate']/.95,bounds['development_author_cluster95_lower']/.5]
        row['goal_selection_metrics']=dict(**bounds,rule_version=2,normalized_constraints=normalized,
            rule='Fair mirror development primary: both goals met first; otherwise worst normalized progress (BattleAI/.95, author cluster95 lower/.50). Once both met prefer higher BattleAI rate. Old unequal-army stress only breaks ties. Final thresholds unchanged.')
    metrics=row['goal_selection_metrics']
    return rank(row,metrics)
