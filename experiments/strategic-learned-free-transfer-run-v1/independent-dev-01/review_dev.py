"""Actually rerun completed DEV raw audits and full CPU proposals; never starts native/GPU."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;RUN=HERE.parent
sys.path.insert(0,str(RUN))
import pipeline_common as c
sys.path.insert(0,str(c.BASE))
from broker import Broker
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--dev',type=Path,default=c.LAB/'evaluations/strategic-learned-free-transfer-dev-01');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 outer=read(a.dev/'PLAN.json');result=read(a.dev/'RESULT.json');assert result['passed'] and len(result['pairs'])==8
 c.require_qualification();c.validate_capsule(c.DEFAULT_CAPSULE)
 frozen=outer['input_sha256'];assert all(sha(path)==h for path,h in frozen.items())
 models={arm:Broker('new-policy',Path(path)) for arm,path in outer['model_paths'].items()}
 assert models['a'].model_sha256=='83319be8bde5d94eea839b1a889821449a7c1492c65da7ca6cde2deb63aab25a'
 assert models['b'].model_sha256=='6dd26e29b55364c293d9874c36a743e4636bcd0208daf5e61042e1f8b506ea00'
 a.out.mkdir(parents=True,exist_ok=False);cases=[];bycase={};total=0
 for index,pair in enumerate(result['pairs']):
  assert pair['job']['seed']==2026103800+index
  for arm in ['a','b']:
   case=a.dev/f'pair-{index:02d}'/arm;n=case/'native';dest=a.out/f'raw-{index:02d}-{arm}'
   proc=subprocess.run([sys.executable,str(RUN/'audit_game_v6.py'),str(n),str(dest)],capture_output=True,text=True,env=dict(os.environ,CUDA_VISIBLE_DEVICES=''))
   (a.out/f'audit-{index:02d}-{arm}.log').write_text(proc.stdout+'\nSTDERR:\n'+proc.stderr);assert proc.returncode==0
   audit=read(dest/'AUDIT.json');assert audit==read(case/'raw-audit/AUDIT.json')
   plan=read(n/'PLAN.json');c.validate_native_epoch(audit,plan,read(n/'EXECUTION.json'))
   assert all(sha(path)==h for path,h in plan['hashes'].items()) and all(sha(n/name)==h for name,h in audit['raw_sha256'].items())
   proposals=rows(n/'agent/typed-broker.jsonl');events=rows(dest/'events.jsonl');sent={e['decision_id']:e for e in events if e['event']=='native_action_sent' and e['decision_id'] is not None}
   assert len(sent)==len(proposals)==audit['counts']['new_policy_decisions']
   assert len({e['native_request_id'] for e in sent.values()})==len(sent)
   for prop in proposals:
    q=prop['request'];r=prop['response'];raw=(n/f"agent/request-{q['request_id']:08d}.json").read_bytes()
    assert json.loads(raw)==q and sha(n/f"agent/request-{q['request_id']:08d}.json")==r['request_sha256']
    assert prop==models[arm].propose(raw,q['request_id'])
    assert sent[q['request_id']]['candidate']==q['candidates'][r['selected_index']]
   win=audit['winner']==('red' if plan['owned_player']==0 else 'blue');assert win is pair['arms'][arm]['win'] and audit['counts']==pair['arms'][arm]['counts']
   end=next(e for e in reversed(rows(n/'strategy-trace.jsonl')) if e['event'] in ['victory','defeat'])
   income=sum(p['response']['op']=='build' and p['request']['candidates'][p['response']['selected_index']]['category']=='income' for p in proposals)
   cases.append(dict(pair=index,arm=arm,win=win,terminal_day=end['day'],counts=audit['counts'],income_builds=income,prewindow_transfers=audit['prewindow_evidence']['prewindow_transfers'],decisions=len(proposals),model_sha256=models[arm].model_sha256,raw_audit_exact=True,all_cpu_proposals_exact=True))
   bycase[index,arm]=proposals;total+=len(proposals);print(json.dumps(dict(completed=len(cases),total=16,full_cpu_proposals=total)),flush=True)
 pairs=[]
 for i in range(8):
  aa,bb=bycase[i,'a'],bycase[i,'b'];prefix=0;different=None
  for x,y in zip(aa,bb):
   if x['request']!=y['request']:break
   prefix+=1
   if different is None and x['response']['selected_index']!=y['response']['selected_index']:different=prefix
  pairs.append(dict(pair=i,first_request_equal=aa[0]['request']==bb[0]['request'],same_request_prefix=prefix,first_different_selection_on_equal_request=different))
 assert all(sha(path)==h for path,h in frozen.items())
 summary={arm:dict(wins=sum(x['win'] for x in cases if x['arm']==arm),builds=sum(x['counts']['policy_builds'] for x in cases if x['arm']==arm),income_builds=sum(x['income_builds'] for x in cases if x['arm']==arm),policy_end_turns=sum(x['counts']['policy_end_turns'] for x in cases if x['arm']==arm),prewindow_transfers=sum(x['prewindow_transfers'] for x in cases if x['arm']==arm)) for arm in ['a','b']}
 report=dict(passed=True,actual_raw_audits_rerun=16,full_cpu_proposals_actually_recomputed=total,all_frozen_source_capsule_raw_hashes_passed=True,summary=summary,cases=cases,pairs=pairs,qualification_fixture_excluded=True,gpu_restore_rerun=False,native_runs=0,gpu_runs=0,optimizer_steps_executed=0)
 (a.out/'REVIEW.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['cases','pairs']},indent=2))
if __name__=='__main__':main()
