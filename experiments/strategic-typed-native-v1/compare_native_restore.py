"""Exact real typed checkpoint/game start-boundary recovery comparison."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations')
A=ROOT/'typed-schema4-policy-fullgame-02';B=ROOT/'typed-schema4-turnstart-restore-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ae=json.loads((A/'EXECUTION.json').read_text());be=json.loads((B/'EXECUTION.json').read_text())
assert ae['game_completed'] and be['game_completed'] and be['native_load_verified']
checks={}
for name in ['strategy-decisions.jsonl','strategy-trace.jsonl','strategy-trace.jsonl.targets.jsonl','typed.jsonl','agent/typed-broker.jsonl']:
    assert (A/name).read_bytes()==(B/name).read_bytes(),name
    checks[name]={'exact_bytes':True,'sha256':sha(A/name)}
for pattern in ['request-????????.json','action-????????.json']:
    an=sorted(p.name for p in (A/'agent').glob(pattern));bn=sorted(p.name for p in (B/'agent').glob(pattern))
    assert an==bn and len(an)==275
    assert all((A/'agent'/n).read_bytes()==(B/'agent'/n).read_bytes() for n in an)
    checks[pattern]={'files':len(an),'exact_bytes':True}
save=A/'data/vcmi/Saves/director-v5-initial.vsgm1'
assert save.read_bytes()==(B/'data/vcmi/Saves/resume-snapshot.vsgm1').read_bytes()
for path in [HERE/'native-fullgame-raw-audit-02/AUDIT.json',HERE/'native-restore-raw-audit-01/AUDIT.json']:
    audit=json.loads(path.read_text());assert audit['whole_game_valid'] and audit['native_apply_markers']==304
out=HERE/'native-restore-exact-01';out.mkdir(exist_ok=False)
result={'passed_exact':True,'checkpoint_load_device':'cpu','policy':'frozen schema4 argmax','native_load_verified':True,
        'save_sha256':sha(save),'checks':checks,'actions_each':304,'policy_decisions_each':275,'optimizer_steps':0,
        'scope':'Native day1 own-turn-start save. Not arbitrary midturn/battle or new-schema PPO optimizer/RNG resume.'}
(out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
