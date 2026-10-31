"""Descriptive role/army-balance diagnostics, excluding all final-test results."""
import json
from pathlib import Path

r=Path('/mnt/g/Heroes3-AI-Lab/research')
rows=json.loads((r/'goal-v5-validation.json').read_text())
cases={c['id']:c for filename in ['scenarios-v2.json','diverse-curriculum.json'] for c in json.loads((r/filename).read_text())}
results=[]
for row in rows:
    for key in ['validation_report','upstream_validation_report','development_validation_report','development_upstream_validation_report']:
        games=json.loads(Path(row[key]).read_text())['battles']
        groups={}
        for game in games:
            army=cases[game['scenario']]['armies']
            side=int(game['role']=='defender')
            counts=[{s['type']:s['amount'] for s in a if s} for a in army]
            delta=[counts[side][name]-counts[1-side][name] for name in counts[side]]
            balance='equal_counts' if all(d==0 for d in delta) else 'own_more' if all(d>=0 for d in delta) else 'own_fewer' if all(d<=0 for d in delta) else 'mixed'
            for group in [game['role'],balance,game['role']+'/'+balance]:groups.setdefault(group,[]).append(game)
        diagnostic=dict(name=row['name'],report=key,groups={})
        for group,games_ in groups.items():
            losses=[g for g in games_ if not g['success']]
            diagnostic['groups'][group]=dict(battles=len(games_),wins=sum(g['success'] for g in games_),
                win_rate=sum(g['success'] for g in games_)/len(games_),
                losses_without_attack=sum(sum(g['action_types'].get(str(i),0) for i in [3,4])==0 for g in losses),
                losses_waiting_over_40percent=sum(g['action_types'].get('0',0)/max(1,g['steps'])>.4 for g in losses),
                truncated=sum(g['truncated'] for g in games_))
        results.append(diagnostic)
(r/'validation-failure-diagnostics.json').write_text(json.dumps(dict(final_test_not_read=True,results=results),indent=2))
for item in results:
    print(item['name'],item['report'],{k:round(v['win_rate'],3) for k,v in item['groups'].items() if '/' not in k})
