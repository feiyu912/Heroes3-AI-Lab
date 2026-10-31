"""Independent completed paired DEV: rerun raw auditors and all actual CPU proposals."""
import argparse,collections,hashlib,json,math,subprocess,sys
from pathlib import Path
ROOT=Path('/mnt/g/Heroes3-AI-Lab');RUN=ROOT/'experiments/strategic-learned-recruitment-run-v1';BASE=ROOT/'experiments/strategic-learned-recruitment-policy-v2'
sys.path.insert(0,str(BASE));sys.path.insert(1,str(RUN))
def load(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(x) for x in Path(p).read_text().splitlines()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--dev',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=load(a.dev/'RESULT.json');plan=load(a.dev/'PLAN.json');assert result['passed'] and len(result['pairs'])==8
 assert plan['training_samples']==plan['optimizer_steps']==0 and not plan['finaltest_touched']
 for f,h in plan['input_sha256'].items():assert sha(f)==h,f
 a.out.mkdir(exist_ok=False,parents=True)
 from broker import Broker
 import torch
 torch.set_num_threads(1)
 reviews=[];inputhashes={};full_replays=0
 for pair in result['pairs']:
  i=pair['index'];qprefix={};current=dict(pair=i,job=pair['job'],arms={})
  assert pair['job']['seed']==2026104000+i and pair['job']['map'] in ['takeover-v2-dev-01-river','takeover-v2-dev-02-reserves']
  for arm in ['baseline','candidate']:
   folder=a.dev/f'pair-{i:02d}'/arm;raw=folder/'native';fresh=a.out/f'raw-{i:02d}-{arm}'
   process=subprocess.run(['/root/heroes3-ai-lab/venv/bin/python',str(RUN/'audit_game_v6.py'),str(raw),str(fresh)],capture_output=True,text=True)
   (a.out/f'raw-{i:02d}-{arm}.log').write_text(process.stdout+'\nSTDERR:\n'+process.stderr);assert process.returncode==0,process.stderr
   audit=load(fresh/'AUDIT.json');assert audit==load(folder/'raw-audit/AUDIT.json')
   nativeplan=load(raw/'PLAN.json');checkpoint=Path(nativeplan['checkpoint']);broker=Broker('new-policy',checkpoint)
   assert broker.model_sha256==plan['model_sha256'][arm] and nativeplan['sampling']=='CPU argmax'
   proposals=rows(raw/'agent/typed-broker.jsonl');qprefix[arm]=[]
   amounts=collections.Counter();buckets=collections.Counter();first_recruit=None
   for number,old in enumerate(proposals,1):
    request=(raw/'agent'/f'request-{number:08d}.json').read_bytes();replay=broker.propose(request,number)
    assert replay==old,(i,arm,number,'full CPU proposal mismatch')
    full_replays+=1;qprefix[arm].append((old['request'],old['response']))
    c=old['request']['candidates'][old['action']]
    if c['op']=='recruit':
     first_recruit=old['request']['day'] if first_recruit is None else first_recruit
     amounts[c['creature_id']]+=c['amount'];buckets[c['quantity_bucket']]+=1
   win=audit['winner']==('red' if pair['job']['player']==0 else 'blue');assert win==pair['arms'][arm]['win']
   assert sha(folder/'raw-audit/AUDIT.json')==pair['arms'][arm]['audit_sha256']
   current['arms'][arm]=dict(win=win,rows=len(proposals),actual_recruits=audit['actual_recruits_checked'],actual_free_transfers=audit['actual_transfers_checked'],builds=audit['counts']['policy_builds'],recruited_quantity=sum(amounts.values()),first_recruit_day=first_recruit,quantity_buckets=dict(buckets))
   inputhashes[str(folder/'raw-audit/AUDIT.json')]=sha(folder/'raw-audit/AUDIT.json')
  prefix=0;first_action_difference=None
  for aa,bb in zip(qprefix['baseline'],qprefix['candidate']):
   if aa[0]!=bb[0]:break
   prefix+=1
   if first_action_difference is None and aa[1]['selected_index']!=bb[1]['selected_index']:first_action_difference=aa[0]['request_id']
  current.update(identical_public_request_prefix=prefix,first_different_action_on_identical_request=first_action_difference)
  reviews.append(current)
 wins={arm:sum(p['arms'][arm]['win'] for p in reviews) for arm in ['baseline','candidate']}
 assert wins['baseline']==result['baseline_wins'] and wins['candidate']==result['candidate_wins']
 summary={arm:{k:sum(p['arms'][arm][k] for p in reviews) for k in ['rows','actual_recruits','actual_free_transfers','builds','recruited_quantity']} for arm in ['baseline','candidate']}
 out=dict(passed=True,actual_raw_audits_rerun=16,all_complete_raw_audits_equal=True,all_full_CPU_proposals_actually_recomputed=full_replays,wins=wins,summary=summary,pairs=reviews,input_sha256=inputhashes,native_runs_by_reviewer=0,GPU_calls=0,optimizer_steps=0,finaltest_touched=False,ability_improvement_claim=False,limitation='Eight paired DEV cells are small and historically seen; no universal win-rate or single-action causality inference')
 (a.out/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['pairs','input_sha256']},indent=2))
if __name__=='__main__':main()
