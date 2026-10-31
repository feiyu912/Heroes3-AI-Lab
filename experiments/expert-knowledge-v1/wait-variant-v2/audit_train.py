"""Cross-check BC first-step records against their actual paired raw battles."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

comparison=json.loads((HERE/'wait-train-comparison.json').read_text())
rows=comparison['results']
samples=[json.loads(line) for line in (HERE/'candidate-bc-train.jsonl').read_text().splitlines() if line]
assert len(rows)==8 and len(samples)==sum(row['benefit_verified'] for row in rows)
by_case={sample['paired_result']['case']:sample for sample in samples}
checks=[]
for row in rows:
    reports=[json.loads((HERE/'wait-runs'/f'{row["case"]}-{kind}.json').read_text()) for kind in ['wait-expert','no-wait-control']]
    assert all(report['terminated'] and not report['truncated'] and report['terminal_outcome']['result_type']==0 and report['invalid_actions']==0 for report in reports)
    assert reports[0]['cross_round_window_verified']
    for report in reports:
        assert all(sha(path)==digest for path,digest in report['source_hashes'].items())
    if row['benefit_verified']:
        sample=by_case[row['case']]
        initial=reports[0]['decisions'][0]
        assert all(sample[key]==value for key,value in initial.items())
        assert sample['action'] in sample['observation']['active_action_ids']
        assert sample['action_type']==0 and sample['split']=='train'
        assert row['wait_success'] and (not row['control_success'] or row['wait_loss']<row['control_loss'])
    checks.append(dict(case=row['case'],normal_pair=True,window_verified=True,benefit_verified=row['benefit_verified']))
result=dict(status='passed',paired_cases=8,actual_battles=16,normal_battles=16,invalid_actions=0,
    verified_first_step_bc_samples=len(samples),negative_or_no_benefit_pairs=8-len(samples),
    fixture_splits={'train':8,'development':4,'test':4},holdout_battles_run=0,
    dataset_sha256=sha(HERE/'candidate-bc-train.jsonl'),comparison_sha256=sha(HERE/'wait-train-comparison.json'),
    checks=checks,limitation='Ghost Dragon aging and stochastic damage not event-level isolated; scope is paired observed benefit and timing, not broad tactical mastery')
(HERE/'dataset-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key not in ['checks']}))
