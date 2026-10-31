"""Read-only, compact status. No train/native/optimizer imports."""
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);f=p/'training.json'
if f.exists():
    d=json.loads(f.read_text());rows=d.get('records',[]);last=rows[-1] if rows else {}
    print(json.dumps(dict(completed=d.get('completed'),error=d.get('error'),updates=len(rows),
        latest={k:last.get(k) for k in ('update','phase','samples','episodes','wins','truncations','actual_Adam_steps','actual_Adam_steps_total','free_mib','checkpoint_sha256')},
        minimum_available_mib=min((r['free_mib'] for r in rows),default=None),maximum_gpu_peak_mib=max((r['gpu_peak_mib'] for r in rows),default=None))))
r=p/'RESULT.json'
if r.exists():
    d=json.loads(r.read_text());print(json.dumps({k:v for k,v in d.items() if k!='DEV'}))
    for x in d.get('DEV',[]):print(json.dumps(dict(model=x['model'],opponent=x['opponent'],summary=x['summary'])))
