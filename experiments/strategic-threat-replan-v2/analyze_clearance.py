"""Archived-state opportunity analysis only: no native action or reward is synthesized."""
import hashlib,json
from pathlib import Path
from clearance_proxy import choose
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations/typed-bounded-replan-paired-01')
assert json.loads((ROOT/'RESULT.json').read_text())['passed']
items=[];inputs={}
for i in range(8):
    root=ROOT/f'pair-{i:02d}/b/native';sidecar=root/'strategy-trace.jsonl.replan.jsonl'
    events=[json.loads(x) for x in sidecar.read_text().splitlines()] if sidecar.exists() else []
    path=root/'agent/typed-broker.jsonl';proposals={p['request']['request_id']:p for p in map(json.loads,path.read_text().splitlines())}
    inputs[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    if sidecar.exists():inputs[str(sidecar)]=hashlib.sha256(sidecar.read_bytes()).hexdigest()
    for e in events:
        p=proposals[e['decision_id']];decision=choose(p['request'],p['response']['selected_index'],e)
        items.append(dict(pair=i,decision_id=e['decision_id'],day=e['day'],proxy=decision))
out=HERE/'clearance-opportunity-01';out.mkdir(exist_ok=False)
report=dict(passed=True,release_states=len(items),coordinate_proxy_overrides=sum(x['proxy']['overridden'] for x in items),
    decisions=items,input_sha256=inputs,proxy_sha256=hashlib.sha256((HERE/'clearance_proxy.py').read_bytes()).hexdigest(),
    native_games=0,optimizer_steps=0,training_samples=0,
    limitation='Only existing legal next-step coordinate opportunities in frozen historical states. No real proxy action, casualty, win or expert utility certification.')
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('decisions','input_sha256')},indent=2))
