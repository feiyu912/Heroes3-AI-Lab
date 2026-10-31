"""Compact read-only status of a known run directory."""
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
for name in ('RESULT.json','training.json','EXECUTION.json','BLOCKED_OR_FAILED.json'):
    path=p/name
    if not path.exists():continue
    d=json.loads(path.read_text());o={k:d[k] for k in ('passed','completed','training_completed','error','checkpoint','checkpoint_sha256','actual_Adam_steps','client_exit','game_completed','transport_drained','accepted_binaries_restored','rebuild_required') if k in d}
    if 'records' in d:
        o['updates']=[{k:r.get(k) for k in ('update','samples','episodes','wins','truncations','actual_Adam_steps','actual_Adam_steps_total','checkpoint_sha256')} for r in d['records']]
    if 'DEV' in d:o['DEV']=d['DEV']
    print(name,json.dumps(o))
