"""New frozen launcher for same planned proxy cells after strict bind-before-transport repair."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPLAN=HERE.parent/'strategic-threat-replan-v2'
source=REPLAN/'paired_proxy.py';text=source.read_text();old_sha=hashlib.sha256(source.read_bytes()).hexdigest()
needle="capsule=LAB/'evaluations/typed-bounded-replan-capsule-01'";assert text.count(needle)==1
text=text.replace(needle,"capsule=LAB/'evaluations/typed-request-bind-director-capsule-01'")
needle="    model=TRAIN/'cuda-curriculum-ack-01/update-1.pt'";assert text.count(needle)==1
text=text.replace(needle,"    assert json.loads((HERE.parent/'strategic-request-bind-barrier-v2/native-repro-comparison-01/AUDIT.json').read_text())['new_execution_certified']\n"+needle,1)
needle="HERE/'audit_replan_v2.py',HERE/'audit_proxy.py',HERE/'PROXY_PLAN.md'";assert text.count(needle)==1
text=text.replace(needle,"HERE/'audit_replan_v2.py',HERE/'audit_proxy.py',HERE/'PROXY_PLAN.md',HERE.parent/'strategic-request-bind-barrier-v2/PLAN.md'",1)
text=text.replace("meaning='Scripted coordinate hypothesis on training diagnostics, not learned or expert behavior.'",
    "meaning='Same preselected proxy cells rerun after aborted strict-binding batch, using Director-only bind-before-transport epoch in BOTH arms. Not fresh independent or learned/expert evidence.'")
dest=REPLAN/'paired_proxy_bind_v2.py';assert not dest.exists();compile(text,str(dest),'exec');dest.write_text(text)
assert hashlib.sha256(source.read_bytes()).hexdigest()==old_sha
(HERE/'PAIRED_RERUN_LAUNCHER.json').write_text(json.dumps(dict(original_unchanged_sha256=old_sha,new_launcher_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
    native_games=0,optimizer_steps=0,scope='Same seeds/method/score endpoints; repaired native epoch and explicit prerequisite'),indent=2))
