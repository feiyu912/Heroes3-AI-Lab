import json,sys
from pathlib import Path
p=Path(sys.argv[1]);rows=[]
for cell in sorted(p.glob('cell-*')):
    a=cell/'admitted/AUDIT.json';n=cell/'native/EXECUTION.json';r={'cell':cell.name}
    if a.exists():
        d=json.loads(a.read_text());r.update({k:d[k] for k in ('passed','samples_admitted','policy_builds','policy_moves','policy_end_turns','native_episode_winner')})
    elif n.exists():
        d=json.loads(n.read_text());r.update({k:d.get(k) for k in ('client_exit','game_completed','stop_reason')})
    rows.append(r)
print(json.dumps(rows))
for name in ('RESULT.json','update-01/RESULT.json'):
    f=p/name
    if f.exists():
        d=json.loads(f.read_text());print(name,json.dumps({k:v for k,v in d.items() if k not in ('episodes','admissions','progress','protocol','completed')}))
