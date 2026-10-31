"""Recompute both boundary audits and compare the matched native request prefixes."""
import argparse,importlib.util,json
from pathlib import Path
from boundary_common import HERE,load,sha,write
spec=importlib.util.spec_from_file_location('_boundary_audit',HERE/'audit_boundary.py');aud=importlib.util.module_from_spec(spec);spec.loader.exec_module(aud)
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 result=dict(passed=False,new_native_games=0,optimizer_steps=0,strength_claim=False,final_test_used=False)
 try:
  reports=[aud.audit(r) for r in [a.baseline,a.candidate]];plans=[load(r/'PLAN.json') for r in [a.baseline,a.candidate]]
  bp,cp=plans;assert bp['arm']=='baseline' and cp['arm']=='candidate'
  for k in ['case','map','seed','owned_player','opponent','seconds','action_schema','contract_sha256']:assert bp[k]==cp[k]
  inputs=set(bp['hashes'])&set(cp['hashes']);assert inputs and all(bp['hashes'][p]==cp['hashes'][p]==sha(p) for p in inputs)
  records=[[json.loads(x) for x in (r/'agent/mechanism-selector.jsonl').read_text().splitlines()] for r in [a.baseline,a.candidate]];br,cr=records
  if bp['case']=='reachable-stock-control':
   assert br[0]['request']==cr[0]['request'] and br[0]['response']==cr[0]['response']
   bq,cq=br[1]['request'],cr[1]['request'];assert {k:v for k,v in bq.items() if k!='candidates'}=={k:v for k,v in cq.items() if k!='candidates'}
   bc,cc=bq['candidates'],cq['candidates'];assert len(cc)==len(bc)+1 and cc[0]==bc[0] and cc[2:]==bc[1:]
   assert cc[1]['op']=='move' and cc[1]['kind']==4 and cc[1]['position']==[29,8,0]
  else:assert len(br)==len(cr) and all(b['request']==c['request'] and b['response']==c['response'] for b,c in zip(br,cr))
  result.update(passed=True,case=bp['case'],matched_native_prefix_verified=True,baseline=reports[0],candidate=reports[1])
 except BaseException as error:result['error']=repr(error);raise
 finally:write(a.out/'AUDIT.json',result)
 print(json.dumps({k:v for k,v in result.items() if k not in ('baseline','candidate')},indent=2))
if __name__=='__main__':main()
