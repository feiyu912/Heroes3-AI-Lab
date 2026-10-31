"""Versioned same-schedule rerun; all arms use the new closed-registry epoch."""
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent/'strategic-director-terminal-drain-v3'
REPLAN=HERE.parent/'strategic-threat-replan-v2'
text=(REPLAN/'paired_proxy_bind_v2.py').read_text()
text=text.replace('import argparse,itertools,json,subprocess','import argparse,itertools,json,subprocess,sys\nsys.path.insert(0,str(Path(__file__).resolve().parent.parent/"strategic-threat-replan-v2"))')
# Path must be imported before adding the established read-only comparison module.
text=text.replace('import argparse,itertools,json,subprocess,sys\nsys.path.insert', 'import argparse,itertools,json,subprocess,sys\nfrom pathlib import Path\nsys.path.insert')
text=text.replace("HERE=Path(__file__).resolve().parent;LAB=", "HERE=Path(__file__).resolve().parent;REPLAN=HERE.parent/'strategic-threat-replan-v2';LAB=")
text=text.replace("assert json.loads((HERE/'proxy-qualification-policy-audit-01/AUDIT.json').read_text())['overrides']>0", "assert json.loads((LAB/'evaluations/typed-director-terminal-drain-qualification-01/RESULT.json').read_text())['passed']")
text=text.replace('typed-request-bind-director-capsule-01','typed-director-terminal-drain-capsule-03')
for name in ('paired_diagnostic.py','clearance_broker.py','clearance_proxy.py','audit_proxy.py','PROXY_PLAN.md'):
    text=text.replace("HERE/'"+name+"'", "REPLAN/'"+name+"'")
text=text.replace("HERE/'run_proxy_game.py'", "HERE/'run_proxy_game_director_drain.py'")
text=text.replace("HERE/'audit_replan_v2.py'", "HERE/'audit_replan_v3.py'")
text=text.replace("HERE.parent/'strategic-typed-native-v1/audit_game_v5.py'", "HERE/'audit_game_v6.py'")
text=text.replace("model,capsule/'EXECUTION.json']", "model,capsule/'EXECUTION.json',capsule/'build-source-manifest.json',HERE/'PLAN.md',HERE/'CANDIDATE_MANIFEST.json',HERE/'director_registry_v1.py',HERE/'audit_game_v6.py']")
text=text.replace("input_sha256=frozen,optimizer_steps=0", "terminal_ack_scope='director',termination_registry_semantics='atomic-termination-closed-registry-v3',input_sha256=frozen,optimizer_steps=0")
text=text.replace("meaning='Same preselected proxy cells rerun after aborted strict-binding batch, using Director-only bind-before-transport epoch in BOTH arms. Not fresh independent or learned/expert evidence.'", "meaning='Same preselected proxy cells rerun after failed transport batches, closed-registry atomic terminal epoch in BOTH arms. Not fresh independent, learned or expert evidence.'")
p=HERE/'paired_proxy_drain_v3.py';assert not p.exists();p.write_text(text)
compile(text,str(p),'exec')
print('Prepared same eight pairs; no games or training launched.')
