"""Actual raw state negative checks; never alters native evidence."""
import copy,json
from pathlib import Path
from audit_mechanism import lines,recruit_state,transfer_state
RAW=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-mechanism-20261023-01')
events=lines(RAW/'typed.jsonl');r=next(e for e in events if e['event']=='recruit_ack_state');c=r['candidate'];b=r['before_state'];a=r['state']
recruit_state(c,b,a)
t=next(e for e in events if e['event']=='free_transfer_native_sent');ta=next(e for e in events if e['event']=='free_transfer_ack_state' and e['native_request_id']==t['native_request_id']);transfer_state(t,ta['before_state'],ta['state'])
checks=[]
def reject(name,fn):
 try:fn()
 except (AssertionError,KeyError,TypeError):checks.append(dict(name=name,rejected=True));return
 raise RuntimeError('invalid evidence accepted: '+name)
for resource in sorted(a['resources']):
 changed=copy.deepcopy(a);changed['resources'][resource]+=1
 reject('wrong_resource_'+resource,lambda:recruit_state(c,b,changed))
changed=copy.deepcopy(a);changed['recruit_stock'][c['level']]['available']+=1
reject('recruit_stock_not_decreased',lambda:recruit_state(c,b,changed))
changed=copy.deepcopy(a);changed['recruit_stock'][c['level']]['creature_ids']=[]
reject('offer_list_changed',lambda:recruit_state(c,b,changed))
changed=copy.deepcopy(a);next(s for s in changed['upper_army'] if s)['count']+=1
reject('destination_extra_soldier',lambda:recruit_state(c,b,changed))
changed=copy.deepcopy(a);changed['visitor']['army_id']+=1
reject('visitor_identity_changed',lambda:recruit_state(c,b,changed))
changed=copy.deepcopy(ta['state']);changed['resources']['gold']-=1
reject('free_transfer_spends_resource',lambda:transfer_state(t,ta['before_state'],changed))
changed=copy.deepcopy(t);changed['amount']-=1
reject('partial_stack_transfer',lambda:transfer_state(changed,ta['before_state'],ta['state']))
out=dict(passed=True,source_raw=str(RAW),actual_baseline_recruit_and_transfer_accepted=True,negative_cases=checks,native_runs=0,gpu_runs=0,optimizer_steps=0,original_evidence_modified=False)
(Path(__file__).parent/'STATE_NEGATIVES.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(passed=True,rejected=len(checks))))
