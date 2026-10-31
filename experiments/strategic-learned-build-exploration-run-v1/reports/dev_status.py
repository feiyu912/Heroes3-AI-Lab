import json,sys
from pathlib import Path
p=Path(sys.argv[1]);r=p/'RESULT.json';f=r if r.exists() else p/'PROGRESS.json'
if f.exists():
    d=json.loads(f.read_text());pairs=d.get('pairs',d.get('completed_pairs',[]))
    print(json.dumps(dict(file=f.name,passed=d.get('passed'),completed_pairs=len(pairs),
        baseline_wins=d.get('baseline_wins'),candidate_wins=d.get('candidate_wins'),error=d.get('error'),
        builds={a:sum(x['arms'][a]['policy_builds'] for x in pairs) for a in ('a','b')})))
