"""Diagnose the already-frozen candidate; never select a model from final outcomes."""
from collections import defaultdict
import json
from pathlib import Path
from battle_outcome_audit import audit
from lab_io import atomic_json

r=Path(__file__).resolve().parent
selected=json.loads((r/'fresh-selected-vs-battleai.json').read_text())
original=json.loads((r/'fresh-upstream-vs-battleai.json').read_text())
fixtures={case['id']:case for case in json.loads((r/'challenge-holdout.json').read_text())}
key=lambda row:(row['scenario'],row['role'],row['seed'])
baseline={key(row):row for row in original['battles']}
assert len(baseline)==512 and len(selected['battles'])==512
groups=defaultdict(list)
for row in selected['battles']:
    other=baseline[key(row)]
    assert row['scenario'] in fixtures
    composition=','.join(sorted(stack['type'] for stack in fixtures[row['scenario']]['armies'][0] if stack))
    for group in ['all','role:'+row['role'],'composition:'+composition]:
        groups[group].append((row,other))
result={}
for group,pairs in groups.items():
    result[group]=dict(battles=len(pairs),selected_wins=sum(a['success'] for a,b in pairs),
        public_wins=sum(b['success'] for a,b in pairs),
        gained=sum(a['success'] and not b['success'] for a,b in pairs),
        regressed=sum(b['success'] and not a['success'] for a,b in pairs))
report=dict(selected_raw_audit=audit(selected['battles']),public_raw_audit=audit(original['battles']),
    groups=result,scope='Frozen v5 final results. Future research may diagnose these outcomes, but any later model needs a new independent confirmation set. No reranking or replacement of the frozen v5 candidate.',
    frozen_candidate=json.loads((r/'final-policy-freeze.json').read_text())['name'])
atomic_json(r/'frozen-final-diagnostics.json',report)
print(json.dumps(report,indent=2))
