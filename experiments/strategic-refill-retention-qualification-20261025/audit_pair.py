"""Independent matched-arm comparison. Does not trust prior AUDIT passed flags."""
import argparse,json
from pathlib import Path
from common import load,write,sha
from audit_mechanism import audit

def pair(baseline,candidate):
 b=Path(baseline);c=Path(candidate);bp=load(b/'PLAN.json');cp=load(c/'PLAN.json')
 assert bp['arm']=='baseline' and cp['arm']=='candidate' and bp['case']==cp['case']
 for field in ['seed','map','case','owned_player','opponent','classification','seconds','contract_sha256']:assert bp[field]==cp[field]
 # Same actual runtime assets and tools. Capsule and arm-specific source snapshots
 # are checked separately against the only-one-CPP treatment contract.
 common_inputs=set(bp['hashes'])&set(cp['hashes'])
 assert common_inputs
 assert all(bp['hashes'][p]==cp['hashes'][p]==sha(p) for p in common_inputs)
 br=audit(b);cr=audit(c)
 records=[]
 for root in (b,c):records.append([json.loads(x) for x in (root/'agent/mechanism-selector.jsonl').read_text().splitlines()])
 x,y=records
 assert x[0]['request']==y[0]['request'] and x[0]['response']==y[0]['response']
 assert x[1]['request']==y[1]['request'] and x[1]['response']==y[1]['response']
 treatment=bp['case'] in ('positive','full-merge')
 if treatment:
  bq,cq=x[2]['request'],y[2]['request']
  assert {k:v for k,v in bq.items() if k!='candidates'}=={k:v for k,v in cq.items() if k!='candidates'}
  bc,cc=bq['candidates'],cq['candidates']
  assert len(cc)==len(bc)+1 and cc[0]==bc[0] and cc[2:]==bc[1:]
  assert cc[1]['op']=='move' and cc[1]['kind']==4 and cc[1]['position']==y[0]['request']['from']
 else:
  prefix=2 if bp['case']=='empty' else 3
  assert all(x[i]['request']==y[i]['request'] and x[i]['response']==y[i]['response'] for i in range(prefix))
 return dict(schema='refill-retention-pair-independent-v1',passed=True,case=bp['case'],both_whole_games_valid=True,exact_pre_treatment_native_prefix=True,only_registered_refill_candidate_added=treatment,boundary_exception_absent=not treatment,baseline=br,candidate=cr,optimizer_steps=0,strength_claim=False,model_promoted=False,final_test_used=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 try:r=pair(a.baseline,a.candidate)
 except BaseException as error:write(a.out/'AUDIT.json',dict(passed=False,error=repr(error)));raise
 write(a.out/'AUDIT.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ('baseline','candidate')},indent=2))
if __name__=='__main__':main()
