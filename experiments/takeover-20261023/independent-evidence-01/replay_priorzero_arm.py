"""Fresh-process strict epoch-specific CPU replay, independent of evaluation driver."""
import argparse,collections,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--policy',type=Path,required=True);p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.policy))
import torch
torch.set_num_threads(1)
from broker import Broker
def load(p):return json.loads(p.read_text())
def rows(p):return [json.loads(x) for x in p.read_text().splitlines()]
plan=load(a.raw/'PLAN.json');broker=Broker('new-policy',Path(plan['checkpoint']));proposals=rows(a.raw/'agent/typed-broker.jsonl')
assert broker.model_sha256==__import__('hashlib').sha256(Path(plan['checkpoint']).read_bytes()).hexdigest()
counts=collections.Counter();requests=[];recruit_days=[];quantity=0;offers=0;maxgap=-float('inf');townrefills=[]
for number,old in enumerate(proposals,1):
 raw=(a.raw/'agent'/f'request-{number:08d}.json').read_bytes();fresh=broker.propose(raw,number);assert fresh==old,(number,'full CPU proposal mismatch')
 q=fresh['request'];cs=q['candidates'];c=cs[fresh['action']];counts[c['op']]+=1;counts['income_builds']+=c['op']=='build' and c['category']=='income'
 ri=[j for j,t in enumerate(cs) if t['op']=='recruit']
 if ri:
  offers+=1;probs=fresh['probabilities'];maxgap=max(maxgap,max(probs[j] for j in ri)-max(probs[j] for j,t in enumerate(cs) if t['op']!='recruit'))
 if c['op']=='recruit':recruit_days.append(q['day']);quantity+=c['amount']
 if c['op']=='move' and c['kind']==4:
  towns=[t for t in q['own_towns'] if t['position']==c['position']];assert len(towns)==1
  townrefills.append(dict(day=q['day'],stock=towns[0]['army_value'],hero=q['own_army_value']))
 requests.append(dict(request_id=number,request_sha256=fresh['request_sha256'],action=fresh['action'],op=c['op']))
trace=rows(a.raw/'strategy-trace.jsonl');terminal=[r for r in trace if r['event'] in ['victory','defeat']];assert len(terminal)==1
def units(r):return sum(n for h in r['heroes'] for cid,n in h['army'])+sum(n for t in r['towns'] for cid,n in t['army'])
decreases=sum(max(0,units(before)-units(after)) for before,after in zip(trace,trace[1:]))
out=dict(passed=True,CPU_full_proposals_recomputed=len(proposals),model_sha256=broker.model_sha256,policy_directory=str(a.policy),counts=dict(counts),recruit_offer_requests=offers,max_recruit_greedy_probability_gap=None if not offers else maxgap,recruited_quantity=quantity,first_recruit_day=recruit_days[0] if recruit_days else None,terminal_day=terminal[0]['day'],victory=terminal[0]['event']=='victory',terminal_heroes=len(terminal[0]['heroes']),terminal_towns=len(terminal[0]['towns']),terminal_owned_units=units(terminal[0]),observed_owned_unit_count_decreases=decreases,own_town_moves=len(townrefills),stocked_town_moves=sum(t['stock']>0 for t in townrefills),first_stocked_town_move_day=next((t['day'] for t in townrefills if t['stock']>0),None),requests=requests,native_runs=0,GPU_calls=0,optimizer_steps=0)
a.out.write_text(json.dumps(out,indent=2)+'\n')
