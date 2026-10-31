"""Recheck existing validation only; never open the held-out outcomes."""
import json
from pathlib import Path
from battle_outcome_audit import audit
from lab_io import atomic_json

root=Path(__file__).resolve().parent
rows=json.loads((root/'goal-v5-validation.json').read_text())
reports={Path(row[key]) for row in rows for key in ['validation_report','upstream_validation_report',
          'development_validation_report','development_upstream_validation_report']}
checks=[]
for path in sorted(reports):
    data=json.loads(path.read_text());result=audit(data['battles'])
    assert data['summary'][0]['wins']==result['verified_wins']
    assert data['summary'][0]['battles']==result['battles']
    checks.append(dict(report=str(path),**result))
atomic_json(root/'validation-win-semantics-audit.json',dict(passed=True,reports=checks,
    checked_battles=sum(check['battles'] for check in checks),final_results_read=False,
    historical_scores_unchanged=True,scope='Raw flags plus three-stack casualty consistency. Joint terminated/truncated flags never count as wins.'))
print('Validation outcome audit passed:',sum(check['battles'] for check in checks),'battles',flush=True)
