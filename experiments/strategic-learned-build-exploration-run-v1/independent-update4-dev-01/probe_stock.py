import json,re,hashlib
from pathlib import Path
ROOT=Path('/root/heroes3-ai-lab/evaluations/strategic-build-exploration-update4-dev-01')
for pair,q in [(3,160),(7,274)]:
 n=ROOT/f'pair-{pair:02d}/b/native'
 req=json.loads((n/f'agent/request-{q:08d}.json').read_text())
 print('PAIR',pair,'REQUEST',json.dumps(req)[:1400])
 typed=[json.loads(x) for x in (n/'typed.jsonl').read_text().splitlines()]
 print('TYPED',json.dumps([e for e in typed if e.get('decision_id') in [q,q+1]])[:4000])
 ls=(n/'client.log').read_text().splitlines()
 hires=[i for i,s in enumerate(ls) if 'HireHero' in s and 'Registered' in s]
 i=hires[-1]
 print('HIRE RANGE',i+1)
 for j in range(i,min(i+180,len(ls))):
  s=re.sub(r'\x1b\[[0-9;]*m','',ls[j])
  if any(k in s for k in ['Director','HireHero','ArrangeStacks','MoveHero','PackageApplied']): print(j+1,s[:1100])
