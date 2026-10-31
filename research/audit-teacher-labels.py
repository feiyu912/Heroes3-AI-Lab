from collections import defaultdict, Counter
import json
from pathlib import Path

root = Path('/root/heroes3-ai-lab/datasets/teacher-balanced-v1')
groups = defaultdict(list)
action_types = Counter()
for path in root.glob('*/*.json'):
    record = json.loads(path.read_text())
    if 'decisions' not in record:
        continue
    for decision in record['decisions']:
        groups[decision['observation_sha256']].append(dict(action=decision['action'],
            value=record['outcome_value'], battle_id=record['battle_id'], split=record['split']))
        action_types[decision['action_type']] += 1
conflicts = {h: rows for h, rows in groups.items() if len({r['action'] for r in rows}) > 1}
outcome_variation = {h: rows for h, rows in groups.items() if len({r['value'] for r in rows}) > 1}
result = dict(states=len(groups), duplicated_states=sum(len(v) > 1 for v in groups.values()),
              conflicting_teacher_action_states=len(conflicts),
              decisions_in_conflicting_groups=sum(len(v) for v in conflicts.values()),
              outcome_variation_states=len(outcome_variation), action_types=dict(action_types),
              conflict_examples=list(conflicts.items())[:10],
              note='Different future outcomes at identical observations can be legitimate stochastic value targets; conflicting action labels would need explicit alias/tie analysis')
Path('/mnt/g/Heroes3-AI-Lab/research/teacher-label-audit.json').write_text(json.dumps(result, indent=2))
print(json.dumps({k:v for k,v in result.items() if k != 'conflict_examples'}))
