"""Visible strong-enemy observations at the last own turn before hero removal."""
import json
from pathlib import Path
from audit import HERE,lines,sha

source=json.loads((HERE/'AUDIT.json').read_text())
details=json.loads((HERE/'DETAILS.json').read_text())
rows=[]
for ep,detail in zip(source['episodes'],details['episodes']):
    root=Path(ep['native']['run_dir'])
    targets=lines(root/'strategy-trace.jsonl.targets.jsonl')
    for loss in detail['own_hero_disappearances']:
        before=loss['before']
        filtered=[dict(line=i,**r)for i,r in targets if r['day']==before['day'] and r['hero'] in loss['ids'] and r['status']=='strength_filter']
        unique={}
        for r in filtered:unique.setdefault((r['kind'],tuple(r['position']),r['strength']),r)
        rows.append(dict(seed=detail['seed'],last_own_state=before,loss_line=loss['line'],
            native_target_evidence=list(unique.values())))
out=HERE/'THREAT_LOSS_LINKS.json';assert not out.exists()
out.write_text(json.dumps(dict(source_sha256=sha(HERE/'DETAILS.json'),rows=rows),indent=2))
for row in rows:
    if row['seed'] in (2026101913,2026101922,2026101923) and row['loss_line'] in (129,409,193):
        print(json.dumps(row))
