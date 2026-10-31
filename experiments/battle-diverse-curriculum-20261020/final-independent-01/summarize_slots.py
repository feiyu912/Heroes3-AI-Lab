"""Summarize already independently reconstructed terminal masks, not new games."""
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
audit=HERE/'actual-review-02/AUDIT.json';a=json.loads(audit.read_text());assert a['passed']
plan=Path('/root/heroes3-ai-lab/evaluations/battle-diverse60-native-02/PLAN.json');p=json.loads(plan.read_text())
counts=collections.Counter();wins=collections.Counter()
for r in a['TRAIN_per_case_terminals']:
    k=(r['scenario'],r['family'],r['role'],r['opponent']);counts[k]+=r['count']
    if r['outcome']=='win':wins[k]+=r['count']
rows=[]
for phase in p['registered_curriculum']['phases']:
    for r in phase:
        k=(r['scenario_index'],r['family'],r['role'],r['opponent']);n=counts[k]
        rows.append(dict(scenario=k[0],family=k[1],role=k[2],opponent=k[3],normal_terminals=n,wins=wins[k],losses=n-wins[k],bucket='0' if n==0 else '1' if n==1 else '>=2'))
assert len(rows)==240 and sum(r['normal_terminals'] for r in rows)==551
groups={}
for field in ('family','role','opponent'):
    groups[field]=[]
    for value in sorted(set(r[field] for r in rows)):
        selected=[r for r in rows if r[field]==value]
        groups[field].append(dict(value=value,slots=len(selected),buckets=dict(collections.Counter(r['bucket'] for r in selected)),normal_terminals=sum(r['normal_terminals'] for r in selected),wins=sum(r['wins'] for r in selected),losses=sum(r['losses'] for r in selected)))
result=dict(passed=True,source_audit_sha256=hashlib.sha256(audit.read_bytes()).hexdigest(),source_plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),method='Actual raw terminal masks independently reconstructed by audit_final.py, including absent-cell zeros against registered240 slots',overall=dict(collections.Counter(r['bucket'] for r in rows)),groups=groups,slots=rows,new_games=0,optimizer_steps_performed=0)
(HERE/'SLOT_TERMINALS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('slots',)},indent=2))
