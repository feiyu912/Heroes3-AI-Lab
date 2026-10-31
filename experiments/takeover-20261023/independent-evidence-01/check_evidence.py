"""Read-only evidence verification; no native, GPU, model import, or optimizer."""
import hashlib,json
from pathlib import Path
ROOT=Path('/mnt/g/Heroes3-AI-Lab'); OUT=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
paths=[
'experiments/strategic-learned-free-transfer-run-v1/independent-dev-01/review-01/REVIEW.json',
'experiments/strategic-learned-free-transfer-run-v1/independent-dev-01/PAIR06_EVIDENCE.json',
'experiments/strategic-learned-free-transfer-run-v1/independent-dev-01/PROBABILITY_COMPARISON.json',
'experiments/strategic-learned-free-transfer-policy-v1/recovery-audit-01/native-cuda-update1-01/AUDIT.json',
'experiments/battle-diverse-curriculum-20261020/final-independent-01/actual-review-02/AUDIT.json',
'experiments/battle-diverse-curriculum-20261020/final-independent-01/SLOT_TERMINALS.json',
'experiments/battle-diverse-curriculum-20261020/final-independent-01/LEARNING_MAGNITUDE.json',
'experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/PAUSE.json',
'experiments/battle-training-continuation-20261020/monitor-independent-01/two-arm-restoration-01/AUDIT.json',
'experiments/battle-training-continuation-20261020/cuda-restore-parent-01/AUDIT.json',
'maintenance/wsl-cleanup-20261023/SUMMARY.json',
'maintenance/wsl-cleanup-20261023/PROTECTED_BEFORE.json',
'maintenance/wsl-cleanup-20261023/PROTECTED_AFTER.json']
evidence=[]
for name in paths:
 p=ROOT/name
 if not p.exists():
  hits=list((ROOT/Path(name).parent).rglob(Path(name).name));assert len(hits)==1,(name,hits);p=hits[0]
 d=load(p)
 evidence.append(dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size,top_keys=list(d) if isinstance(d,dict) else None))
protected=load(ROOT/'maintenance/wsl-cleanup-20261023/PROTECTED_BEFORE.json')
assert protected==load(ROOT/'maintenance/wsl-cleanup-20261023/PROTECTED_AFTER.json')
checks=[]
for name,expected in protected.items():
 p=Path(name);actual=sha(p);checks.append(dict(path=name,expected=expected,actual=actual,passed=actual==expected))
n=ROOT/'experiments/strategic-learned-recruitment-native-v2';m=load(n/'CANDIDATE_MANIFEST.json')
for p,expected in [(n/'CANDIDATE_MANIFEST.json','865988a27bc8de8f257b767ac5b10927e76da96fe974e37414fe7519f38e7830'),(n/'CONTRACT.md',m['contract_sha256']),(n/'build_capsule.py',m['build_driver_sha256'])]+[(n/'candidate'/r,e['candidate_sha256']) for r,e in m['files'].items()]:
 actual=sha(p);checks.append(dict(path=str(p),expected=expected,actual=actual,passed=actual==expected))
a=dict(scope='current byte SHA checks and historical evidence reading; historical auditors not rerun',native_runs=0,gpu_runs=0,optimizer_steps=0,evidence=evidence,byte_checks=checks,all_byte_checks_passed=all(c['passed'] for c in checks),cleanup_protected_before_equals_after=True)
bindings=[]
for item in evidence:
 d=load(Path(item['path']))
 for key in ['input_sha256']:
  for name,expected in d.get(key,{}).items():
   p=Path(name);actual=sha(p)
   bindings.append(dict(path=name,expected=expected,actual=actual,passed=actual==expected,source=item['path']))
a['historical_direct_input_bindings']=bindings
a['historical_direct_input_bindings_passed']=all(c['passed'] for c in bindings)
(OUT/'AUDIT.json').write_text(json.dumps(a,indent=2)+'\n')
print(json.dumps(dict(evidence=len(evidence),byte_checks=len(checks),passed=a['all_byte_checks_passed'],historical_bindings=len(bindings),historical_bindings_passed=a['historical_direct_input_bindings_passed']),indent=2))
