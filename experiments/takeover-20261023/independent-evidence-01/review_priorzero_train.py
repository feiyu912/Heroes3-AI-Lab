"""Actual post-training independent CPU raw-auditor rerun and sealed sample review."""
import argparse,collections,hashlib,json,math,subprocess,sys
from pathlib import Path
ROOT=Path('/mnt/g/Heroes3-AI-Lab');RUN=ROOT/'experiments/strategic-learned-recruitment-run-v2';BASE=ROOT/'experiments/strategic-learned-recruitment-policy-v3'
sys.path.insert(0,str(BASE));sys.path.insert(1,str(RUN))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(x) for x in Path(p).read_text().splitlines()]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--train',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
 result=load(a.train/'RESULT.json');assert result['passed'] and len(result['episodes'])==8
 update=load(a.train/'update-01/RESULT.json');assert update['completed_update'] and update['training_updates']==1
 a.out.mkdir(exist_ok=False,parents=True);cells=[];samples=[];episodes=[];input_hashes={}
 from load_admitted import load as sealed_load
 from pipeline_common import validate_cells
 for i in range(8):
  cell=a.train/f'cell-{i:02d}';review=a.out/f'raw-{i:02d}'
  proc=subprocess.run(['/root/heroes3-ai-lab/venv/bin/python',str(RUN/'audit_game_v6.py'),str(cell/'native'),str(review)],capture_output=True,text=True)
  (a.out/f'audit-{i:02d}.log').write_text(proc.stdout+'\nSTDERR:\n'+proc.stderr);assert proc.returncode==0,proc.stderr
  fresh=load(review/'AUDIT.json');original=load(cell/'raw-audit/AUDIT.json');assert fresh==original,'complete raw audit differs'
  ss,ee,cert=sealed_load(cell/'admitted');samples.extend(ss);episodes.extend(ee)
  proposals=rows(cell/'native/agent/typed-broker.jsonl');assert len(ss)==len(proposals)==fresh['actual_decisions_checked']
  for s,p in zip(ss,proposals):
   assert s['request']==p['request'] and s['action']==p['action'] and s['old_logprob']==p['old_logprob'] and s['old_value']==p['old_value']
   assert s['request_sha256']==p['request_sha256'] and s['policy_sha256']==p['model_sha256']
   assert s['request']['candidates'][s['action']]['op']==s['action_type']
  assert cert['replay_actions_logprobs_values_rng_exact'] and cert['sampling_device']=='cuda'
  totals=collections.Counter();buckets=collections.Counter();creatures=collections.Counter();quantity=0
  for s in ss:
   c=s['request']['candidates'][s['action']]
   if c['op']=='recruit':
    quantity+=c['amount'];buckets[c['quantity_bucket']]+=1;creatures[c['creature_id']]+=c['amount']
    for resource,amount in c['cost'].items():totals[resource]+=amount
  cells.append(dict(cell=i,rows=len(ss),reward=ee[0]['reward'],job=ee[0]['job'],actual_recruits=fresh['actual_recruits_checked'],actual_free_transfers=fresh['actual_transfers_checked'],builds=fresh['counts']['policy_builds'],recruited_quantity=quantity,recruit_quantity_buckets=dict(buckets),recruit_resource_spending=dict(totals),creatures=dict(creatures),all_raw_audits_equal=True))
  input_hashes[str(cell/'admitted/AUDIT.json')]=sha(cell/'admitted/AUDIT.json')
 validate_cells(episodes);assert any(s['action_type']=='recruit' for s in samples)
 import torch,model_io
 torch.set_num_threads(1)
 final,bundle,digest=model_io.load_model(Path(update['checkpoint']),'cpu');assert digest==update['checkpoint_sha256']
 parent,pb,psha=model_io.load_model(BASE/'initialization-02/recruitment-initialization.pt','cpu');assert bundle['parent_checkpoint_sha256']==psha
 # CPU recompute the archived selected-action logp/value; CUDA Generator action
 # reproducibility remains the separately hash-verified actual CUDA certificate.
 max_logp_error=0.;max_value_error=0.
 with torch.no_grad():
  for sample in samples:
   logits,value=parent(**model_io.architecture.encoder.collate([sample['request']],'cpu'))
   actual_logp=float(logits[0].log_softmax(-1)[sample['action']]);actual_value=float(value[0])
   max_logp_error=max(max_logp_error,abs(actual_logp-sample['old_logprob']));max_value_error=max(max_value_error,abs(actual_value-sample['old_value']))
   assert math.isclose(actual_logp,sample['old_logprob'],rel_tol=2e-5,abs_tol=2e-5)
   assert math.isclose(actual_value,sample['old_value'],rel_tol=2e-5,abs_tol=2e-5)
 assert bundle['training_updates']==1 and bundle['optimizer_steps_total']==update['optimizer_steps_total'] and bundle['snapshot_device']=='cuda'
 assert model_io.steps(bundle['optimizer'])==update['optimizer_steps_total'] and bundle['complete_update_boundary']
 groups={}
 for group in ['actor','critic','recruit_actor','recruit_critic']:
  deltas=[v.double()-parent.state_dict()[n].double() for n,v in final.state_dict().items() if n.startswith(group+'.')]
  groups[group]=dict(changed_tensors=sum(bool(d.ne(0).any()) for d in deltas),l2=math.sqrt(sum(float(d.square().sum()) for d in deltas)),max_abs=max(float(d.abs().max()) for d in deltas))
 out=dict(passed=True,actual_raw_audits_rerun=8,all_complete_raw_audits_equal=True,CUDA_onpolicy_certificates_read_and_hash_verified=8,CUDA_replay_independently_rerun=False,CPU_proposals_independently_recomputed=False,samples=len(samples),episodes=len(episodes),wins=sum(e['reward']==1 for e in episodes),losses=sum(e['reward']==-1 for e in episodes),actual_recruits=sum(c['actual_recruits'] for c in cells),actual_free_transfers=sum(c['actual_free_transfers'] for c in cells),recruited_quantity=sum(c['recruited_quantity'] for c in cells),cells=cells,checkpoint_sha256=digest,initial_sha256=psha,actual_reported_CUDA_Adam_steps=update['cuda_optimizer_steps'],full_saved_Adam_checked=True,CPU_final_model_loaded=True,parameter_delta=groups,recruit_bias_initial=float(parent.actor.recruit_bias.detach()),recruit_bias_final=float(final.actor.recruit_bias.detach()),input_sha256=input_hashes,native_runs_by_reviewer=0,GPU_calls=0,optimizer_steps_by_reviewer=0,ability_improvement_claim=False)
 out.update(CPU_full_NN_selected_action_logp_value_recomputed=len(samples),CPU_vs_saved_CUDA_max_logp_error=max_logp_error,CPU_vs_saved_CUDA_max_value_error=max_value_error,CPU_CUDA_comparison_tolerance=dict(relative=2e-5,absolute=2e-5))
 (a.out/'AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['cells','input_sha256']},indent=2))
if __name__=='__main__':main()
