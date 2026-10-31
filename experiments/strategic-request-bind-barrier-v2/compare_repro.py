"""Read-only exact failing-cell comparison; preserve original audit-invalid status."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/root/heroes3-ai-lab/evaluations/typed-clearance-proxy-paired-01/pair-02/b/native')
NEW=Path('/root/heroes3-ai-lab/evaluations/typed-request-bind-repro-01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proof=json.loads((HERE/'native-repro-proxy-audit-01/AUDIT.json').read_text());assert proof['passed']
def files(root):return {str(p.relative_to(root)) for pattern in ['request-*.json','action-*.json'] for p in (root/'agent').glob(pattern)}
a,b=files(OLD),files(NEW);assert a==b
names=sorted(a)+['strategy-decisions.jsonl','strategy-trace.jsonl','strategy-trace.jsonl.targets.jsonl','agent/typed-broker.jsonl']
different=[name for name in names if sha(OLD/name)!=sha(NEW/name)]
def early_applies(root):
    sent=set();early=[];applies=0
    for number,line in enumerate((root/'client.log').read_text(errors='replace').splitlines(),1):
        if 'DirectorTypedEvent ' in line:
            e=json.JSONDecoder().raw_decode(line.split('DirectorTypedEvent ',1)[1])[0]
            if e['event']=='native_action_sent':sent.add((e['player'],e['native_request_id'],e['op']))
        if 'TypedActionApplied ' in line:
            m=re.search(r'TypedActionApplied player=(\d+) native_request_id=(\d+) op=(move|end_turn) success=([01])',line)
            if m and int(m[1])==0:
                assert m[4]=='1';applies+=1;key=(int(m[1]),int(m[2]),m[3])
                if key not in sent:early.append(dict(line=number,request_id=key[1],op=key[2]))
    return dict(applies=applies,apply_before_context=early)
old,new=early_applies(OLD),early_applies(NEW)
assert old['apply_before_context'] and not new['apply_before_context']
out=HERE/'native-repro-comparison-01';out.mkdir(exist_ok=False)
report=dict(passed=True,all_policy_and_gameplay_files_exact=not different,files_compared=len(names),different_files=different,
    old_transport=old,new_transport=new,original_experiment_still_invalid=True,original_outcome_scored=False,
    new_execution_certified=True,new_proxy_overrides=proof['overrides'],optimizer_steps=0,training_samples=0,
    raw_sha256={str(p):sha(p) for p in [OLD/'client.log',NEW/'client.log',HERE/'native-repro-raw-audit-01/AUDIT.json']})
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
