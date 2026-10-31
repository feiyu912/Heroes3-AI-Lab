"""Visible-state failure analysis of the eight fixed NK development games."""
from pathlib import Path
import json,re,sys
BASE=Path('/mnt/g/Heroes3-AI-Lab/experiments/strategic-economy-v4/acceptance-06')
sys.path.insert(0,str(BASE.parent.parent/'strategic-policy-v2'))
from audit_supply_raw import records,sha
def distance(a,b):
 return max(abs(a[0]-b[0]),abs(a[1]-b[1])) if a[2]==b[2] else None
def visible(row,path):
 threats=[dict(t,grid_distance=distance(row['from'],t['position']),
               ratio=t['approx_army_value']/row['own_army_value'])
          for t in row['visible_threats'] if row['own_army_value']>0]
 towns=[dict(t,grid_distance=distance(row['from'],t['position']))for t in row['own_towns']]
 supply=[dict(index=i,**c)for i,c in enumerate(row['candidates'])if c['kind']==4]
 return dict(file=str(path),sha256=sha(path),request_id=row['request_id'],day=row['day'],
             position=row['from'],own_army_value=row['own_army_value'],movement=row['movement'],
             threats=threats,own_towns=towns,supply_candidates=supply,candidate_count=len(row['candidates']))
results=[]
execution=json.loads((BASE/'EXECUTION.json').read_text());assert execution['status']=='completed'
for episode in execution['episodes'][4:]:
 audit=json.loads(Path(episode['audit']).read_text());raw=audit['raw'];main=raw['original_main_id']
 native=Path(raw['native_dir']);agent=Path(raw['agent_dir']);states=records(native/'strategy-trace.jsonl')
 commits=[v for _,v in records(agent/'broker-trace.jsonl')if v['event']=='decision_committed']
 requests=[]
 absence=raw['original_main_first_absent'];loss=raw['original_main_loss_day']
 before_moves=[line for line,s in states if s['event']=='before_move']
 assert len(before_moves)==len(commits)
 for commit,trace_line in zip(commits,before_moves):
  path=agent/commit['request_file'];r=json.loads(path.read_text())
  if r['hero']==main and (absence is None or trace_line<absence['line']):requests.append((r,path))
 views=[visible(r,p)for r,p in requests]
 strong=next((v for v in views if any(t['ratio']>=1.5 for t in v['threats'])),None)
 nearby=next((v for v in views if any(t['ratio']>=1.5 and t['grid_distance']is not None and t['grid_distance']<=8 for t in v['threats'])),None)
 before=[(line,s)for line,s in states if absence is None or line<absence['line']]
 last=before[-1]if before else None
 lastmain=next(((line,s)for line,s in reversed(before)if any(h['id']==main for h in s['heroes'])),None)
 window=[v for v in views if loss is None or loss-7<=v['day']<=loss]
 opportunities=[v for v in window if v['supply_candidates'] and any(t['army_value']>0 for t in v['own_towns'])]
 logs=(native/'client.log').read_text(errors='replace').splitlines()
 removes=[i for i,s in enumerate(logs)if re.search(r'removing object id='+str(main)+r';',s)]
 pivot=removes[0]if removes else len(logs)
 battle_evidence=[dict(line=i+1,text=re.sub(r'\x1b\[[0-9;]*m','',s))for i,s in enumerate(logs[:pivot])if 'Starting battle of'in s][-8:]
 preceding_turnend=next(((line,s['event'])for line,s in reversed(before)if s['event']in ('turn_end','before_move','native_battle_blocked')),None)
 block_index=next((i for i in range(len(before)-1,-1,-1)if before[i][1]['event']=='native_battle_blocked'),None)
 previous_driver=None
 if block_index is not None:
  previous_driver=next(((line,s['event'])for line,s in reversed(before[:block_index])if s['event']in ('turn_end','before_move','turn_start')),None)
 results.append(dict(tag=episode['tag'],won=raw['won'],days=raw['native_days'],main_status=raw['original_main_status'],
  main_loss_day=loss,main_first_absent=absence,main_removal_log=raw['original_main_removal_log'],
  first_visible_enemy_ge_1_5x=strong,first_visible_enemy_ge_1_5x_within_grid8=nearby,
  last_main_request=views[-1]if views else None,last_main_present_state=lastmain,
  loss_battle_previous_driver=previous_driver,loss_battle_log_evidence=battle_evidence,
  final_seven_days_supply_candidate_opportunities=opportunities,
  final_seven_days_requests=len(window),delivered_count=raw['delivered_count'],
  delivery_days=[dict(day=d['day'],count=d['count'])for d in raw['deliveries']],
  recruited_types=audit['recruited_creature_types'],build_events=audit['build_events'],
  evidence_sha256=raw['evidence_sha256']))
out=Path(__file__).parent/'NK06_FAILURE_ANALYSIS.json';assert not out.exists()
out.write_text(json.dumps(dict(schema='nk06-visible-failure-analysis-v1',threshold='Diagnostic fixed enemy/own >=1.5, near Chebyshev<=8; coordinate proxy only, not native interception forecast',episodes=results),indent=2))
print(json.dumps([{k:r[k]for k in ('tag','won','days','main_loss_day','main_status','loss_battle_previous_driver','final_seven_days_requests')}for r in results],indent=2))
