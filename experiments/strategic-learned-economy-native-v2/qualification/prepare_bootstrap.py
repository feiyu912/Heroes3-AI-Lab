"""Derive CPU-only mechanism collector and unweakened whole-game raw auditor."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent.parent/'strategic-learned-build-exploration-run-v1'
def once(t,a,b):assert t.count(a)==1,(a,t.count(a));return t.replace(a,b,1)
t=(OLD/'continuation-dev-tools/collect_cpu.py').read_text()
t=once(t,'LOCAL=DEV_TOOLS.parent','LOCAL=DEV_TOOLS\nOLD=LOCAL.parent.parent/"strategic-learned-build-exploration-run-v1"')
t=once(t,"BASE=LOCAL.parent/'strategic-learned-build-exploration-policy-v1'","BASE=LOCAL.parent.parent/'strategic-learned-build-exploration-policy-v1'")
t=once(t,"LEGACY=LOCAL.parent/'strategic-typed-training-v1'","LEGACY=LOCAL.parent.parent/'strategic-typed-training-v1'")
t=once(t,'assert args.map in ("takeover-v2-dev-01-river","takeover-v2-dev-02-reserves"),"Only the two registered DEV maps"','assert args.map in ("takeover-v2-train-01-mines","takeover-v2-train-02-development"),"Mechanism-only uses fixed TRAIN maps"')
t=once(t,"choices=['takeover-v2-dev-01-river','takeover-v2-dev-02-reserves'],default='takeover-v2-dev-01-river'","choices=['takeover-v2-train-01-mines','takeover-v2-train-02-development'],default='takeover-v2-train-02-development'")
t=once(t,"LAB_ADV_LEARNED_ECONOMY='build_v1'","LAB_ADV_THREAT_REPLAN='off',LAB_ADV_LEARNED_ECONOMY='build_v1'")
t=once(t,"LOCAL/'collect_episode_v5.py'","OLD/'collect_episode_v5.py'")
(HERE/'collect_mechanism.py').write_text(t)
t=(OLD/'audit_game_v6.py').read_text()
t=once(t,"HERE=Path(__file__).resolve().parent","HERE=Path(__file__).resolve().parent\nsys.path.append(str(HERE.parent.parent/'strategic-learned-build-exploration-run-v1'))")
t=once(t,"candidate_manifest['schema']=='director-learned-economy-build-v1'","candidate_manifest['schema']=='director-learned-economy-free-stock-prewindow-v2'")
t=once(t,"(out/'events.jsonl').write_text", "from flow_evidence import verify as verify_flow\nreport.update(prewindow_evidence_verified=True,prewindow_evidence=verify_flow(raw,proposals,folder=folder))\n(out/'events.jsonl').write_text")
(HERE/'audit_game_v6.py').write_text(t)
print('CPU mechanism collector and strict raw audit derived; no native/GPU execution.')
