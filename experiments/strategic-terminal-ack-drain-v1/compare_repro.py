"""Raw paired regression: identical game/actions, real terminal EndTurn ACK now delivered."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=Path('/root/heroes3-ai-lab/evaluations/typed-onpolicy-balanced-01/cell-02/native')
NEW=Path('/root/heroes3-ai-lab/evaluations/typed-terminal-ack-repro-01')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks={}
for name in ['strategy-decisions.jsonl','strategy-trace.jsonl','strategy-trace.jsonl.targets.jsonl','agent/typed-broker.jsonl']:
    assert (OLD/name).read_bytes()==(NEW/name).read_bytes(),name
    checks[name]={'exact_bytes':True,'sha256':sha(OLD/name)}
for pattern in ['request-????????.json','action-????????.json']:
    names=sorted(p.name for p in (OLD/'agent').glob(pattern));assert names==sorted(p.name for p in (NEW/'agent').glob(pattern)) and len(names)==100
    assert all((OLD/'agent'/n).read_bytes()==(NEW/'agent'/n).read_bytes() for n in names)
    checks[pattern]={'files':len(names),'exact_bytes':True}
old=[json.loads(s) for s in (OLD/'typed.jsonl').read_text().splitlines()]
new=[json.loads(s) for s in (NEW/'typed.jsonl').read_text().splitlines()]
assert not any(r['event']=='package_applied' and r.get('native_request_id')==330 for r in old)
ack=[r for r in new if r['event']=='package_applied' and r.get('native_request_id')==330]
assert len(ack)==1 and ack[0]['op']=='end_turn' and ack[0]['decision_id'] is None and ack[0]['success'] is True
terminal=next(i for i,r in enumerate(new) if r['event']=='game_over')
ackindex=next(i for i,r in enumerate(new) if r in ack);assert ackindex>terminal
assert not any(r['event']=='native_action_sent' for r in new[terminal+1:])
log=(NEW/'client.log').read_text(errors='replace')
assert 'Auto-test shutdown deferred: pending native request acknowledgments' in log
assert 'Ending game after native ACK drain.' in log
audit=json.loads((HERE/'native-repro-raw-audit-01/AUDIT.json').read_text());assert audit['whole_game_valid'] and not audit['contract_errors'] and audit['winner']=='blue'
out=HERE/'regression-exact-01';out.mkdir(exist_ok=False)
result=dict(passed=True,gameplay_and_policy_traces_exact=True,checks=checks,terminal_auto_endturn_request_id=330,
    true_ACK_after_game_over_observed=True,new_action_after_terminal=False,original_failed_evidence_preserved=True,
    unchanged_outcome='Director red normal defeat day12: seven days without town',new_policy_samples=0,optimizer_steps=0,
    scope='Transport/lifecycle regression, not an ability improvement or a second independent capability sample.')
(out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
