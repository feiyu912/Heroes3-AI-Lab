"""Record a validation-driven population alignment before final outcomes exist."""
import hashlib
import json
from pathlib import Path
import time
from goal_selection import rank
from lab_io import atomic_json

root=Path(__file__).resolve().parent
assert not (root/'final-policy-freeze.json').exists() and not list(root.glob('fresh-*-vs-*.json'))
cases=json.loads((root/'scenarios-v2.json').read_text())
stress=[]
for case in cases[20:26]:
    quantities=[{stack['type']:stack['amount'] for stack in army if stack} for army in case['armies']]
    stress.append(dict(case=case['id'],same_creature_counts=quantities[0]==quantities[1]))
assert any(not case['same_creature_counts'] for case in stress)
rows=json.loads((root/'goal-v5-validation.json').read_text())
basis=[dict(name=row['name'],old_battleai_wins=row['validation']['wins'],
    old_author_wins=row['upstream_validation']['wins'],mirror_battleai_wins=row['development_validation']['wins'],
    mirror_author_wins=row['development_upstream_validation']['wins'],battles_per_condition=48)
    for row in rows if row['name'] in ['v5-diverse-last-64','v5-diverse-last-128']]
assert len(basis)==2
def probe(battle,lower,old=0.):
    row=dict(development_validation=dict(win_rate=battle,mean_permanent_units_lost=10.),
        development_upstream_validation=dict(win_rate=.7),validation=dict(win_rate=old),upstream_validation=dict(win_rate=old))
    return rank(row,dict(development_author_cluster95_lower=lower))
assert probe(.96,.51)>probe(1.,.49), 'Both actual goals precede a one-sided score'
assert probe(1.,.51)>probe(.96,.7), 'Once both goals met, prefer closer to 100% BattleAI'
assert probe(.96,.51,0.)>probe(.91,.6,1.), 'Unequal-army stress cannot override achieved mirror goals'
atomic_json(root/'goal-selection-mirror-alignment.json',dict(rule_version=2,declared_unix=time.time(),
    basis=basis,old_validation_stress_cases=stress,final_outcomes_read=False,
    prior_rule='goal-selection-plan.json retained; initially all old/diverse constraints entered the minimum',
    primary='Diverse equal-army development only: BattleAI >=.95 and author scenario-cluster95 lower >.50',
    ranking='Both goals met first; if met prefer higher BattleAI rate; otherwise maximize worst normalized mirror progress. Old unequal-army stress only diagnostic/tie-breaker.',
    final_thresholds_unchanged=True,final_scenarios=32,battles_per_final_matchup=512,
    holdout_definition_sha256=hashlib.sha256((root/'challenge-holdout.json').read_bytes()).hexdigest(),
    rank_semantics_contract_passed=True,
    scope='Validation-driven rule correction after B trade-off, before final test; not preregistered at experiment start. Existing training lineages remain unchanged.'))
print('Declared fair-mirror rule v2;',sum(not case['same_creature_counts'] for case in stress),'of 6 old validation cases have unequal creature counts',flush=True)
