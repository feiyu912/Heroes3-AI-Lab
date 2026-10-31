"""Exercise real archived transfer windows and complete harness freeze, no games."""
import ast
import json
from pathlib import Path
from audit_supply_raw import records,army,sha
from run_supply_pilot import frozen_inputs,verify,CHECKPOINT,HERE


def main():
    for name in ('run_supply_pilot.py','audit_supply_raw.py'):
        ast.parse((HERE/name).read_text())
    manifest=frozen_inputs(CHECKPOINT)
    verify(manifest)
    evidence=HERE.parent/'strategic-nk-failure-audit-20261018/AUDIT.json'
    source=json.loads(evidence.read_text())
    pairs=[]
    for ep in source['episodes']:
        path=Path(ep['native']['run_dir'])/'strategy-trace.jsonl'
        assert sha(path)==ep['evidence'][str(path)]
        states=records(path)
        for j,(line,s) in enumerate(states):
            if s['event']!='before_army_transfer':continue
            next_line,after=states[j+1]
            assert after['event']=='economy_applied'
            hb={h['id']:army(h) for h in s['heroes']};ha={h['id']:army(h) for h in after['heroes']}
            tb={t['id']:army(t) for t in s['towns']};ta={t['id']:army(t) for t in after['towns']}
            hg=[ha[k]-hb[k] for k in hb if ha[k]!=hb[k]]
            tl=[tb[k]-ta[k] for k in tb if tb[k]!=ta[k]]
            assert len(hg)==len(tl)==1 and hg[0] and hg[0]==tl[0]
            pairs.append(dict(trace=str(path),before_line=line,after_line=next_line,
                creatures=dict(hg[0]),count=sum(hg[0].values())))
    out=HERE/'supply-harness-preflight-01';assert not out.exists();out.mkdir()
    report=dict(schema='supply-harness-cpu-preflight-v1',passed=True,
        syntax=True,frozen_input_manifest_verified=True,frozen=manifest,
        archived_transfer_windows=len(pairs),archived_transferred_troops=sum(r['count'] for r in pairs),
        transfer_conservation_verified=True,pairs=pairs,games_launched=0,
        complete_native_v3_episode_audit_executed=False,source_audit_sha256=sha(evidence))
    (out/'PREFLIGHT.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items()if k not in ('frozen','pairs')}))


if __name__=='__main__':main()
