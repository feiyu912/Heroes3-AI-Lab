"""Algebra over existing TRAIN gradient statistics, with explicit coverage bounds."""
from pathlib import Path
import json,math,statistics,hashlib
H=Path(__file__).resolve().parent;P=H.parents[2]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stats(v):return dict(n=len(v),min=min(v),median=statistics.median(v),mean=statistics.mean(v),max=max(v))
def main():
 source=P/'experiments/ubuntu-native-takeover-20261025/gradient-support/actual-02/AUDIT.json';d=load(source);assert d['passed'] and d['TRAIN_rows']==512 and d['chronological_groups_per_variant']==32 and d['DEV_rows_used']==d['optimizer_steps']==0
 inputpaths=[source,P/'experiments/ubuntu-native-takeover-20261025/gradient-support/diagnose.py',P/'research/masked_ppo.py',P/'research/full_graph_policy.py',P/'research/recovered-graph.py']
 assert sha(inputpaths[1])==d['script_sha256']
 frozen=load(P/'experiments/battle-observed-MC-probe-20261024/SOURCE_FREEZE.json');pin=frozen.get('files',frozen.get('input_sha256',{}))
 assert sha(P/'research/masked_ppo.py')==pin['/mnt/g/Heroes3-AI-Lab/research/masked_ppo.py']
 assert 'clip_grad_norm_(model.parameters(), 0.5)' in (P/'research/masked_ppo.py').read_text()
 rows=[];summaries={};roles={}
 for target in ['reference','mc']:
  group=[]
  for i in range(32):
   rs=[r for r in d['rows'] if r['target']==target and r['chronological_batch']==i];assert {r['role'] for r in rs}=={'attacker','defender'}
   assert all(r['tensor_support_intersection']==r['scalar_support_intersection']==r['dot']==0 for r in rs)
   a=math.sqrt(sum(r['actor_norm']**2 for r in rs));v=math.sqrt(sum(r['weighted_critic_norm']**2 for r in rs));n=math.hypot(a,v);coefficient=min(1.,.5/(n+1e-6));actoronly=min(1.,.5/(a+1e-6))
   r=dict(target=target,chronological_batch=i,actor_body_norm=a,weighted_critic_body_norm=v,combined_body_norm=n,full_gradient_norm_lower_bound=n,full_clip_coefficient_upper_bound=coefficient,full_clip_must_activate_at_common_theta=n>.5,body_only_clip_coefficient=coefficient,body_only_actor_only_clip_coefficient=actoronly,body_only_actor_suppression_from_critic=1-coefficient/actoronly,body_only_critic_squared_norm_share=v*v/(a*a+v*v),actual_full_parameter_clip_measured=False)
   group.append(r);rows.append(r)
  summaries[target]=dict(groups=32,must_clip_common_theta_groups=sum(r['full_clip_must_activate_at_common_theta'] for r in group),combined_body_norm=stats([r['combined_body_norm'] for r in group]),actor_body_norm=stats([r['actor_body_norm'] for r in group]),weighted_critic_body_norm=stats([r['weighted_critic_body_norm'] for r in group]),clip_coefficient_upper_bound=stats([r['full_clip_coefficient_upper_bound'] for r in group]),body_only_extra_actor_suppression=stats([r['body_only_actor_suppression_from_critic'] for r in group]),body_only_extra_actor_suppression_gt5pct=sum(r['body_only_actor_suppression_from_critic']>.05 for r in group),body_only_extra_actor_suppression_gt10pct=sum(r['body_only_actor_suppression_from_critic']>.1 for r in group))
  for role in ['attacker','defender']:
   rs=[r for r in d['rows'] if r['target']==target and r['role']==role];roles[target+'/'+role]=dict(actor_body_norm=stats([r['actor_norm'] for r in rs]),weighted_critic_body_norm=stats([r['weighted_critic_norm'] for r in rs]))
 hist=P/'experiments/ubuntu-native-takeover-20261025/restored-history/root/heroes3-ai-lab/evaluations/battle-observed-MC-probe-01'
 rp=hist/'REFERENCE_REPRODUCTION.json';mp=hist/'RESULT.json';assert sha(rp)=='dc0471e1181d969aa5f14d760a843aae20811e4020dcfe8c388813c47b55c7df' and sha(mp)=='63f8497fd276ded2bea3dc7b2265d66f822fb20119c79966108cb0de0292e7fd'
 actual=dict(reference=dict(actual_Adam=load(rp)['actual_Adam'],metrics=load(rp)['metrics']),mc=dict(actual_Adam=load(mp)['MC_new_branch_Adam'],metrics=load(mp)['MC_metrics']))
 inputpaths+=[rp,mp,P/'experiments/battle-observed-MC-probe-20261024/learner.py',P/'experiments/takeover-20261023/diagnose_MC_gradient_geometry.py',H/'ADAM_HISTORY.json']
 result=dict(passed=True,method='no neural recompute; exact arithmetic over saved body L2 norms, critic already multiplied by .5, orthogonal supports permit Pythagoras',scope='common theta61 chronological16-row groups, not actual shuffled8 Adam steps; policy/value heads excluded',TRAIN_rows=512,targets=['reference','mc'],summaries=summaries,by_role=roles,rows=rows,historical_actual_update_metrics=actual,actual_step_clip_frequency_available=False,actual_step_clip_factors_available=False,heads_in_gradient_statistics=False,full_parameter_gradient_vectors_available=False,common_theta_complete_body_clipping_occurrence=64,new_neural_forwards=0,new_native_games=0,new_optimizer_steps=0,new_DEV_analysis=False,GPU_operations=0,input_sha256={str(p):sha(p) for p in inputpaths})
 (H/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(summaries=summaries,actual_average_gradient_norm={k:v['metrics']['gradient_norm'] for k,v in actual.items()}),indent=2))
if __name__=='__main__':main()
