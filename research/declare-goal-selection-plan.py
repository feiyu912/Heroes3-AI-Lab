"""Record validation-driven selection adaptation before any full-graph trial."""
import json
from pathlib import Path
import time
from goal_selection import score
from lab_io import atomic_json

r=Path('/mnt/g/Heroes3-AI-Lab/research')
assert not (r/'v5-diverse-last.json').exists() and not (r/'v5-diverse-all.json').exists()
assert not (r/'fresh-challenge-results.json').exists()
rows=json.loads((r/'goal-v5-validation.json').read_text())
row=dict(name='v5-diverse-heads-128')
for prefix in ['', 'upstream_', 'development_', 'development_upstream_']:
    report=r/f'v5-diverse-heads-128-{prefix}validation.json'
    row[prefix+'validation_report']=str(report)
    row[prefix+'validation']=json.loads(report.read_text())['summary'][0]
rows.append(row)
diagnostics=[]
for candidate in rows:
    result=score(candidate)
    diagnostics.append(dict(name=candidate['name'],score=result,metrics=candidate['goal_selection_metrics']))
    print(candidate['name'],result,flush=True)
atomic_json(r/'goal-selection-plan.json',dict(declared_unix=time.time(),
    adaptation_after_head128_validation=True,before_full_graph_training=True,before_final_test=True,
    unchanged_final_success_conditions=['BattleAI independent win rate >=95%',
        'Direct public MMAI independent scenario-cluster95 lower bound >50%'],
    selection='Maximize worst normalized progress over both validation sets: BattleAI/.95, direct-opponent cluster95 lower/.50; tie-break by BattleAI sum, source lower, source sum, casualties',
    validation_diagnostics=diagnostics,
    reason='Equal raw max-min wins can prefer balanced mediocre results over a model meeting unequal user thresholds. Success is still assessed only on untouched final games.'))
