"""Public-state DEV behavior strata; never interprets them as teacher targets."""
import collections,hashlib,json
from pathlib import Path
DEV=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-dev-20261023-01');OUT=Path(__file__).parent/'dev-actual-01'
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]
records=[]
for i in range(8):
 for arm in ['baseline','candidate']:
  work=DEV/f'pair-{i:02d}'/arm/'native';proposals=rows(work/'agent/typed-broker.jsonl');trace=rows(work/'strategy-trace.jsonl');events=rows(work/'typed.jsonl')
  ending=[r for r in trace if r['event'] in ['victory','defeat']];assert len(ending)==1
  offers=[];townmoves=[];incomebuilds=0;builds=0
  selected_recruit=[];max_recruit_advantage=[]
  for p in proposals:
   q=p['request'];cs=q['candidates'];chosen=cs[p['action']];ri=[j for j,c in enumerate(cs) if c['op']=='recruit']
   if ri:
    probs=p['probabilities'];recruitmax=max(probs[j] for j in ri);othermax=max(probs[j] for j,c in enumerate(cs) if c['op']!='recruit')
    offers.append(dict(request_id=q['request_id'],day=q['day'],candidate_count=len(ri),total_probability=sum(probs[j] for j in ri),max_probability=recruitmax,max_nonrecruit_probability=othermax,greedy_gap=recruitmax-othermax))
   if chosen['op']=='recruit':selected_recruit.append(q['day'])
   if chosen['op']=='build':builds+=1;incomebuilds+=chosen['category']=='income'
   if chosen['op']=='move' and chosen['kind']==4:
    towns=[t for t in q['own_towns'] if t['position']==chosen['position']];assert len(towns)==1
    townmoves.append(dict(day=q['day'],stock_army=towns[0]['army_value'],hero_army=q['own_army_value']))
  def units(state):return sum(n for h in state['heroes'] for cid,n in h['army'])+sum(n for t in state['towns'] for cid,n in t['army'])
  decreases=0;town_disappearances=0;hero_disappearances=0
  for before,after in zip(trace,trace[1:]):
   decreases+=max(0,units(before)-units(after))
   town_disappearances+=len({t['id'] for t in before['towns']}-{t['id'] for t in after['towns']})
   hero_disappearances+=len({t['id'] for t in before['heroes']}-{t['id'] for t in after['heroes']})
  records.append(dict(pair=i,arm=arm,victory=ending[0]['event']=='victory',terminal_day=ending[0]['day'],terminal_hero_count=len(ending[0]['heroes']),terminal_town_count=len(ending[0]['towns']),terminal_owned_units=units(ending[0]),observed_owned_unit_count_decreases=decreases,observed_town_disappearances=town_disappearances,observed_hero_disappearances=hero_disappearances,builds=builds,income_builds=incomebuilds,own_town_moves=len(townmoves),stocked_town_moves=sum(r['stock_army']>0 for r in townmoves),first_stocked_town_move_day=next((r['day'] for r in townmoves if r['stock_army']>0),None),recruits=len(selected_recruit),recruit_offer_requests=len(offers),max_single_recruit_probability=max((r['max_probability'] for r in offers),default=None),max_recruit_vs_nonrecruit_greedy_gap=max((r['greedy_gap'] for r in offers),default=None),recruit_offers=offers))
summary={arm:{k:sum(r[k] for r in records if r['arm']==arm) for k in ['builds','income_builds','own_town_moves','stocked_town_moves','recruits','recruit_offer_requests','observed_owned_unit_count_decreases','observed_town_disappearances','observed_hero_disappearances']} for arm in ['baseline','candidate']}
out=dict(passed=True,scope='actual public DEV requests/probabilities/trace behavior counts, separate from win rate',summary=summary,records=records,loss_limitations='Count decreases and actor/town disappearances across actual public snapshots are not independently certified battle casualties; can include ownership changes or other causes. No hidden enemy state or optimal-action labels.',native_runs=0,GPU_calls=0,optimizer_steps=0)
(OUT/'BEHAVIOR.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(summary,indent=2))
