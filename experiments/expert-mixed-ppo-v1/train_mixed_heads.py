"""Isolated cached-head reference PPO; launched only under controller's flock."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import random
import shutil
import time
import numpy as np
from common import HERE,RESEARCH,PUBLIC,read,digest,module,verify_plan,FrozenExpert,FragmentTracker


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--plan',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--lock-fd',required=True,type=int)
    parser.add_argument('--resume-checkpoint')
    args=parser.parse_args()
    lock_path=Path('/proc/self/fd')/str(args.lock_fd)
    assert lock_path.resolve()==Path('/root/heroes3-ai-lab/evaluations/.pool-lock')
    fcntl.flock(args.lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    plan=read(args.plan);verify_plan(plan)
    assert plan['finalized_for_execution'], 'Draft plans cannot launch training'
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
    import torch
    from lab_io import atomic_json
    from gpu_opponent import OpponentVector
    from reference_ppo import update,encode_reference,distribution,gae
    from full_graph_policy import potential
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    torch.manual_seed(plan['seed']);np.random.seed(plan['seed']);random.seed(plan['seed'])
    graph=module('mixed_recovered_graph',RESEARCH/'recovered-graph.py')
    initial=args.resume_checkpoint or plan['initial_checkpoint']
    learner=graph.RecoveredPair(initial).cuda().eval()
    for name,parameter in learner.named_parameters():
        parameter.requires_grad_('policy_head__' in name or 'value_head__' in name)
    reference=graph.RecoveredPair(plan['reference_checkpoint']).cuda().eval();reference.requires_grad_(False)
    assert not ({parameter.data_ptr() for parameter in learner.parameters()} & {parameter.data_ptr() for parameter in reference.parameters()})
    reference_versions=[parameter._version for parameter in reference.parameters()]
    frozen_body={name:parameter._version for name,parameter in learner.named_parameters() if not parameter.requires_grad}
    optimizer=torch.optim.Adam([parameter for parameter in learner.parameters() if parameter.requires_grad],lr=plan['learning_rate'])
    previous=0;previous_steps=0;closed_fragments=[]
    counters={category:{role:dict(decisions=0,normal_outcomes=0,wins=0,losses=0,truncations=0)
        for role in ['attacker','defender']} for category in plan['categories']}
    if args.resume_checkpoint:
        saved=torch.load(args.resume_checkpoint,map_location='cpu',weights_only=True)
        assert saved['algorithm']=='expert-mixed-reference-PPO' and saved['finetuning_mode']=='heads'
        assert saved['plan_sha256']==digest(args.plan) and saved['config']==plan
        assert saved['completed_updates']%16==0 and saved['environment_steps']==saved['completed_updates']*24*32
        optimizer.load_state_dict(saved['optimizer_state_dict'])
        torch.set_rng_state(saved['torch_rng_state']);torch.cuda.set_rng_state_all(saved['cuda_rng_states'])
        random.setstate(saved['python_rng_state'])
        state=saved['numpy_rng_state']
        np.random.set_state((state['kind'],np.asarray(state['keys'],np.uint32),state['pos'],state['has_gauss'],state['cached_gauss']))
        previous=saved['completed_updates'];previous_steps=saved['environment_steps'];counters=saved['training_counters']
        closed_fragments=saved['closed_fragments']
    assert previous<plan['updates']
    expert=FrozenExpert(plan)
    run_id=str(time.time_ns())
    folder=Path('/root/heroes3-ai-lab/models/expert-mixed-ppo-v1')/run_id
    folder.mkdir(parents=True)
    source=folder/'source';source.mkdir()
    shutil.copyfile(args.plan,source/'plan.json')
    for index,(path,sha) in enumerate(plan['dependency_sha256'].items()):
        if Path(path).suffix in ['.py','.sh']:
            shutil.copyfile(path,source/(str(index)+'-'+Path(path).name))
    vector=None;records=[];started=time.monotonic();latest=initial
    try:
        for iteration in range(previous,plan['updates']):
            if vector is None or iteration%16==0:
                if vector:vector.close();vector=None
                phase=iteration//16;rows=plan['phases'][phase]
                configs=[]
                for index,row in enumerate(rows):
                    config=dict(row['config'])
                    config['worker_root']=str(Path(config['worker_root'])/run_id)
                    configs.append(config)
                expert.verify()
                vector=OpponentVector(configs,'/root/heroes3-ai-lab/venv/bin/python',expert)
                fragment_tracker=FragmentTracker(24)
                current=learner.encode_features([state['features'] for state in vector.states])
            samples=[];actions=[];old_logp=[];values=[];next_values=[];rewards=[];terms=[];truncs=[]
            ref_logp=[];ref_ids=[];candidate_ids=[];tick=time.monotonic()
            for _ in range(plan['rollout']):
                raw=[state['features'] for state in vector.states]
                ref=encode_reference(reference,raw,graph.head_collate,batch_size=24)
                ref_logp.extend(ref['log_probs']);ref_ids.extend(ref['action_ids']);candidate_ids.extend([sample[2].tolist() for sample in current])
                with torch.inference_mode():
                    batch=graph.head_collate(current,'cuda');logits,value=learner(*batch)
                    dist=distribution(logits,batch[-1]);chosen=dist.sample();logp=dist.log_prob(chosen)
                samples.extend(current);actions.extend(chosen.tolist());old_logp.extend(logp.tolist());values.append(value.cpu().numpy())
                transitions=vector.step([sample[2][action] for sample,action in zip(current,chosen.tolist())])
                fragment_tracker.observe(transitions)
                current=learner.encode_features([state['features'] for state in transitions])
                with torch.inference_mode():
                    _,next_value=learner(*graph.head_collate(current,'cuda'));nv=next_value.cpu().numpy().copy()
                    for index,state in enumerate(transitions):
                        if state['truncated'] and not state['terminated']:
                            _,final=learner(*graph.head_collate(learner.encode_features([state['final_features']]),'cuda'))
                            nv[index]=float(final)
                adjusted=[]
                for row,old,state in zip(rows,raw,transitions):
                    bucket=counters[row['category']][row['config']['role']];bucket['decisions']+=1
                    if state['terminated'] and not state['truncated']:
                        outcome=json.loads(json.dumps(state['outcome']))
                        from battle_outcome_audit import audit
                        won=bool(not state['truncated'] and outcome and outcome['result_type']==0 and outcome['winner']==int(row['config']['role']=='defender'))
                        audit([dict(terminated=True,truncated=state['truncated'],terminal_outcome=outcome,role=row['config']['role'],success=won)])
                        bucket['normal_outcomes']+=1;bucket['wins']+=int(won);bucket['losses']+=int(not won)
                    elif state['truncated']:bucket['truncations']+=1
                    nxt=0. if state['terminated'] else potential(state['final_features'] if state['truncated'] else state['features'])
                    adjusted.append(state['reward']+plan['shaping']*(plan['gamma']*nxt-potential(old)))
                next_values.append(nv);rewards.append(adjusted)
                terms.append([state['terminated'] for state in transitions]);truncs.append([state['truncated'] for state in transitions])
            advantages,returns=gae(rewards,values,next_values,terms,truncs,gamma=plan['gamma'],lam=plan['gae_lambda'])
            metrics=update(learner,optimizer,samples,actions,old_logp,np.asarray(values).reshape(-1),advantages.reshape(-1),returns.reshape(-1),
                epochs=3,batch_size=64,entropy_coef=plan['entropy_coef'],collate_fn=graph.head_collate,
                recompute_batch_size=24,recompute_atol=2e-4,recompute_rtol=0.,reference_coef=plan['reference_coef'],
                reference_log_probs=ref_logp,reference_action_ids=ref_ids,candidate_action_ids=candidate_ids,reference_parameters=tuple(reference.parameters()))
            assert reference_versions==[parameter._version for parameter in reference.parameters()]
            assert frozen_body=={name:parameter._version for name,parameter in learner.named_parameters() if not parameter.requires_grad}
            expert.verify()
            mem={key:int(value.strip().split()[0]) for key,value in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
            assert mem['MemAvailable']>2*1024*1024 and mem['SwapTotal']-mem['SwapFree']<256*1024
            record=dict(update=iteration+1,samples=len(samples),metrics=metrics,steps_per_second=len(samples)/(time.monotonic()-tick),
                category_role_counts=json.loads(json.dumps(counters)),expert_requests=expert.delegate.requests,
                expert_safe_multi_proxy=expert.delegate.safe_multi_selected,certified_tactic_success=None)
            records.append(record)
            if (iteration+1)%16==0:
                close_info=fragment_tracker.close_summary(rows,'finish' if iteration+1==plan['updates'] else 'rotation')
                close_info.update(after_update=iteration+1,phase=phase)
                vector.close();vector=None
                closed_fragments.append(close_info);record['phase_close']=close_info
                state=np.random.get_state()
                target=folder/('update-'+str(iteration+1)+'.pt');assert not target.exists()
                learner.save(str(target),algorithm='expert-mixed-reference-PPO',finetuning_mode='heads',completed_updates=iteration+1,
                    environment_steps=(iteration+1)*24*32,plan_sha256=digest(args.plan),config=plan,
                    optimizer_state_dict=optimizer.state_dict(),torch_rng_state=torch.get_rng_state(),cuda_rng_states=torch.cuda.get_rng_state_all(),
                    python_rng_state=random.getstate(),numpy_rng_state=dict(kind=state[0],keys=state[1].tolist(),pos=state[2],has_gauss=state[3],cached_gauss=state[4]),training_counters=counters,closed_fragments=closed_fragments,
                    continuation_note='Restore optimizer/RNG at 16-update phase boundary; simulator states restart from frozen next-phase configs.')
                latest=str(target)
            report=dict(completed=False,CUDA_training=True,checkpoint=latest,checkpoint_sha256=digest(latest),latest_update=iteration+1,config=plan,
                plan_sha256=digest(args.plan),records=records,source_snapshot=str(source),resumed_from_update=previous,
                training_counters=counters,closed_fragments=closed_fragments,
                discarded_ongoing_fragments=sum(item['discarded_ongoing_fragments'] for item in closed_fragments),
                independent_confirmation_run=False,goal_achieved=False)
            atomic_json(args.output,report);print(record,flush=True)
        if vector:vector.close();vector=None
        report.update(completed=True,all_workers_exit_zero=True)
        atomic_json(args.output,report)
    finally:
        if vector:vector.abort()


if __name__=='__main__':main()
