"""Additional real native-binding anchors; never infer timing from next decision."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'strategic-threat-replan-v2'))
from causal_stability_audit_v2 import sha,parse_log,movement_comparison
out=HERE/'independent-paired-04';proof_path=out/'AUDIT.json'
proof=json.loads(proof_path.read_text());assert proof['passed'] and proof['native_games_reaudited']==16
inputs={str(proof_path):sha(proof_path),str(Path(__file__)):sha(Path(__file__))};pairs=[]
for pair in proof['pairs']:
    n=pair['first_override']
    if n is None:continue
    moves=[];intervals=[];anchors=[]
    for arm in ['a','b']:
        raw=Path('/root/heroes3-ai-lab/evaluations/typed-clearance-proxy-paired-04')/f"pair-{pair['pair']:02d}"/arm/'native/client.log'
        inputs[str(raw)]=sha(raw);parsed=parse_log(raw.read_text(errors='replace'))
        sent=parsed['sent'][n];release=next(e['line'] for e in parsed['releases'] if e['event']['decision_id']==n)
        assert release<sent
        moves.append([e for e in parsed['movements'] if e['line']<sent])
        intervals.append([e for e in parsed['movements'] if release<e['line']<sent]);anchors.append(dict(arm=arm,release_line=release,native_action_sent_line=sent))
    pairs.append(dict(pair=pair['pair'],decision_id=n,anchors=anchors,complete_pre_native_binding_server_prefix=movement_comparison(*moves),
                      movements_between_release_and_binding=intervals,
                      limitation='Actual pre-dispatch native_action_sent anchors, with actual request ID binding proven by independent whole-game contract. Recorded movement projection only, not hidden world state.'))
assert all(sha(Path(p))==h for p,h in inputs.items())
report=dict(passed=True,pairs=pairs,input_sha256=inputs,new_native_games=0,GPU_operations=0)
(out/'PREFIX_BINDING_AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
