"""Pair06 public-observation fork and own logistics; no hidden enemy/save state."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;DEV=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-free-transfer-dev-01')
def rows(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def choose(p):return p['request']['candidates'][p['response']['selected_index']]
def main():
 data={arm:rows(DEV/f'pair-06/{arm}/native/agent/typed-broker.jsonl') for arm in ['a','b']}
 prefix=[];fork=None;firstdifferent=None
 for i,(a,b) in enumerate(zip(data['a'],data['b'])):
  if a['request']!=b['request']:
   firstdifferent=dict(index=i+1,a=a['request'],b=b['request']);break
  prefix.append(i+1)
  if choose(a)!=choose(b) and fork is None:fork=dict(index=i+1,request=a['request'],initial_response=a['response'],trained_response=b['response'],initial_candidate=choose(a),trained_candidate=choose(b))
 report=dict(pair=6,same_first_request=data['a'][0]['request']==data['b'][0]['request'],equal_request_prefix=len(prefix),first_different_action_on_identical_request=fork,first_different_following_request=firstdifferent,arms={})
 for arm,ps in data.items():
  n=DEV/f'pair-06/{arm}/native';trace=rows(n/'strategy-trace.jsonl');raw=n.joinpath('client.log').read_text(errors='replace');lines=[re.sub(r'\x1b\[[0-9;]*m','',s) for s in raw.splitlines()]
  audit=json.loads((n.parent/'raw-audit/AUDIT.json').read_text());assert all(sha(n/name)==h for name,h in audit['raw_sha256'].items())
  end=next(x for x in reversed(trace) if x['event'] in ['victory','defeat'])
  ownlast={}
  for p in ps:
   for town in p['request']['own_towns']:ownlast[town['town_id']]=dict(request_id=p['request']['request_id'],day=p['request']['day'],own_turn=p['request']['own_turn'],town=town)
  last=ps[-1];q=last['request'];same_turn=[p for p in ps if p['request']['own_turn']==q['own_turn']]
  prior=same_turn[-2] if len(same_turn)>1 else None
  economy=[x for x in trace if x['event'] in ['before_hire_hero','before_army_transfer','before_recruit','economy_applied']]
  report['arms'][arm]=dict(last_request=q,last_response=last['response'],last_candidate=choose(last),last_same_turn_prior_selected_goal=choose(prior) if prior else None,terminal=end,last_observed_own_towns=list(ownlast.values()),
   own_turn_initial_requests=[dict(request=p['request'],selected=choose(p)) for i,p in enumerate(ps) if i==0 or p['request']['own_turn']!=ps[i-1]['request']['own_turn']],
   early_decisions=[dict(request=p['request'],selected=choose(p)) for p in ps[:min(8,len(ps))]],public_logistics=economy,
   terminal_native_lines=[dict(line=i+1,text=s) for i,s in enumerate(lines) if any(k in s for k in ['DaysWithoutTown','PlayerEndsGame','BattleResultsApplied','RemoveObject','native gameOver'])][-20:],
   raw_sha256=audit['raw_sha256'],counts=audit['counts'],prewindow_transfers=audit['prewindow_evidence']['prewindow_transfers'])
 (HERE/'PAIR06_EVIDENCE.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(equal_request_prefix=len(prefix),fork_index=fork['index'] if fork else None,fork_a=fork['initial_candidate'] if fork else None,fork_b=fork['trained_candidate'] if fork else None,arms={arm:dict(lastday=v['last_request']['day'],laststrength=v['last_request']['own_army_value'],lasttowns=len(v['last_request']['own_towns']),lastgoal=v['last_candidate'],terminalday=v['terminal']['day'],terminalheroes=v['terminal']['heroes'],terminaltowns=v['terminal']['towns'],prewindow=v['prewindow_transfers']) for arm,v in report['arms'].items()}),indent=2))
if __name__=='__main__':main()
