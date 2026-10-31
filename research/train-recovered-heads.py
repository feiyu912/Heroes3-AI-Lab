"""Adapt official v15 actor/critic heads via masked PPO with frozen graph encoders."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np


def main():
    import torch
    from vector_env import VectorEnv
    import decision_model
    from masked_ppo import gae,distribution,update
    from lab_io import atomic_json,capture_source
    r=Path('/mnt/g/Heroes3-AI-Lab/research')
    spec=importlib.util.spec_from_file_location('recovered_graph',r/'recovered-graph.py')
    graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)
    # Reuse the already verified PPO update with the cached embedding batch collator.
    decision_model.collate=graph.head_collate
    p=argparse.ArgumentParser()
    p.add_argument('--workers',type=int,default=24);p.add_argument('--updates',type=int,default=128)
    p.add_argument('--rollout',type=int,default=32);p.add_argument('--seed',type=int,default=20261018)
    p.add_argument('--opponents',nargs='+',default=['BattleAI']);p.add_argument('--checkpoint')
    p.add_argument('--resume',action='store_true')
    p.add_argument('--step-cost',type=float,default=0.002)
    p.add_argument('--scenario-file',default=str(r/'scenarios-v2.json'))
    p.add_argument('--balanced-configs',action='store_true')
    p.add_argument('--shaping',type=float,default=0.)
    p.add_argument('--learning-rate',type=float,default=1e-4)
    p.add_argument('--entropy-coef',type=float,default=.01)
    p.add_argument('--gamma',type=float,default=.99);p.add_argument('--gae-lambda',type=float,default=.95)
    p.add_argument('--native-opponent-device',choices=['cpu','cuda'],default='cuda' if os.environ.get('LAB_NATIVE_ONNX_CUDA')=='1' else 'cpu')
    p.add_argument('--experiment-initial-checkpoint')
    p.add_argument('--first-battle',action='store_true')
    p.add_argument('--output',required=True)
    args=p.parse_args()
    if not args.experiment_initial_checkpoint:args.experiment_initial_checkpoint=args.checkpoint
    assert 0<=args.step_cost<=0.01
    assert 0<args.gamma<=1 and 0<=args.gae_lambda<=1
    assert json.loads((r/'recovered-graph-contract.json').read_text())['passed']
    torch.set_num_threads(2);torch.manual_seed(args.seed)
    pair=graph.RecoveredPair(args.checkpoint).cuda().eval()
    from gpu_opponent import configure_training,OpponentVector
    fixed_opponent=configure_training(args,graph,pair)
    optimizer=torch.optim.Adam([p for p in pair.parameters() if p.requires_grad],lr=args.learning_rate)
    previous_updates=previous_steps=0
    if args.resume:
        state=torch.load(args.checkpoint,map_location='cpu',weights_only=True)
        optimizer.load_state_dict(state['optimizer_state_dict'])
        torch.set_rng_state(state['torch_rng_state'])
        torch.cuda.set_rng_state_all(state['cuda_rng_states'])
        previous_updates=state['completed_updates'];previous_steps=state['environment_steps']
    cases=[c for c in json.loads(Path(args.scenario_file).read_text()) if c['split']=='train']
    run_id=str(time.time_ns());folder=Path('/root/heroes3-ai-lab/models/recovered-ppo')/run_id
    source_snapshot=capture_source(folder,'train-recovered-heads.py')
    records=[];episodes=truncations=wins=0
    started=time.monotonic();configs=[];vector=None
    latest_checkpoint=args.checkpoint
    try:
        for iteration in range(args.updates):
            if iteration%16==0:
                if vector:vector.close()
                phase=(previous_updates+iteration)//16;configs=[]
                rng=np.random.default_rng(args.seed+phase*1777)
                for i in range(args.workers):
                    role='attacker' if (i if args.balanced_configs else phase+i)%2==0 else 'defender'
                    opponent=args.opponents[(i//2 if args.balanced_configs else i)%len(args.opponents)]
                    case=cases[int(rng.integers(len(cases)))] if args.balanced_configs else cases[(phase*args.workers+i)%len(cases)]
                    configs.append(dict(map=case['map'],role=role,
                        initial_reset_once=args.first_battle,
                        seed=args.seed+phase*1000+i,opponent=opponent,feature_version='upstream-graph-v15',step_cost=args.step_cost,
                        opponent_model='DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx' if opponent=='MMAI_MODEL' else None,
                        worker_root=f'/root/heroes3-ai-lab/workers/recovered-{run_id}/{phase}-{i}'))
                vector=(OpponentVector(configs,'/root/heroes3-ai-lab/venv/bin/python',fixed_opponent) if fixed_opponent
                        else VectorEnv(configs,executable='/root/heroes3-ai-lab/venv/bin/python'))
                current=pair.encode_features([s['features'] for s in vector.states])
            samples=[];actions=[];old_logp=[];values=[];next_values=[];rewards=[];terminated=[];truncated=[]
            tick=time.monotonic()
            for _ in range(args.rollout):
                with torch.inference_mode():
                    batch=graph.head_collate(current,'cuda');logits,value=pair(*batch)
                    dist=distribution(logits,batch[-1]);chosen=dist.sample();logp=dist.log_prob(chosen)
                samples.extend(current);actions.extend(chosen.tolist());old_logp.extend(logp.tolist());values.append(value.cpu().numpy())
                old_observations=[s['features'] for s in vector.states] if args.shaping else None
                transitions=vector.step([sample[2][a] for sample,a in zip(current,chosen.tolist())])
                current=pair.encode_features([s['features'] for s in transitions])
                with torch.inference_mode():
                    _,nv=pair(*graph.head_collate(current,'cuda'))
                    nv=nv.cpu().numpy().copy()
                    for i,s in enumerate(transitions):
                        if s['truncated'] and not s['terminated']:
                            final=pair.encode_features([s['final_features']])
                            _,v=pair(*graph.head_collate(final,'cuda'));nv[i]=float(v)
                step_rewards=[s['reward'] for s in transitions]
                if args.shaping:
                    from full_graph_policy import potential
                    for i,(old,s) in enumerate(zip(old_observations,transitions)):
                        nxt=0. if s['terminated'] else potential(s['final_features'] if s['truncated'] else s['features'])
                        step_rewards[i]+=args.shaping*(args.gamma*nxt-potential(old))
                next_values.append(nv);rewards.append(step_rewards)
                terminated.append([s['terminated'] for s in transitions]);truncated.append([s['truncated'] for s in transitions])
                episodes+=sum(s['terminated'] for s in transitions);truncations+=sum(s['truncated'] and not s['terminated'] for s in transitions)
                wins+=sum(s['terminated'] and s['reward']>0 for s in transitions)
            advantage,returns=gae(rewards,values,next_values,terminated,truncated,gamma=args.gamma,lam=args.gae_lambda)
            metrics=update(pair,optimizer,samples,actions,old_logp,np.asarray(values).reshape(-1),
                advantage.reshape(-1),returns.reshape(-1),epochs=3,batch_size=64,entropy_coef=args.entropy_coef,
                recompute_atol=2e-4,recompute_rtol=0.)
            assert truncations<=max(2,episodes*.05),'Excessive truncations'
            mem={k:int(v.strip().split()[0]) for k,v in (l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines())}
            assert mem['MemAvailable']>2*1024*1024 and mem['SwapTotal']-mem['SwapFree']<256*1024, f"Memory reserve: available={mem['MemAvailable']/1024:.1f} MiB, swap_used={(mem['SwapTotal']-mem['SwapFree'])/1024:.1f} MiB"
            record=dict(update=previous_updates+iteration+1,samples=len(samples),steps_per_second=len(samples)/(time.monotonic()-tick),
                episodes=episodes,wins=wins,truncations=truncations,metrics=metrics,free_mib=mem['MemAvailable']/1024,
                gpu_allocated_mib=torch.cuda.max_memory_allocated()/1024**2)
            records.append(record)
            if fixed_opponent:
                fixed_opponent.assert_unchanged()
                record['fixed_opponent']=dict(requests=fixed_opponent.requests,batches=fixed_opponent.batches,
                    inference_seconds=fixed_opponent.seconds,weights_unchanged=True)
            if iteration%16==0:
                values_=subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu,memory.used,utilization.gpu',
                    '--format=csv,noheader,nounits'],text=True).strip().splitlines()[0].split(',')
                record['gpu_telemetry']=dict(zip(['temperature_c','memory_used_mib','utilization_percent'],
                    [float(v.strip()) for v in values_]))
                assert record['gpu_telemetry']['temperature_c']<86 and record['gpu_telemetry']['memory_used_mib']<14000
            if (iteration+1)%16==0 or iteration+1==args.updates:
                pair.save(str(folder/f'update-{previous_updates+iteration+1}.pt'),completed_updates=previous_updates+iteration+1,
                    environment_steps=previous_steps+(iteration+1)*args.workers*args.rollout,config=vars(args),
                    optimizer_state_dict=optimizer.state_dict(),torch_rng_state=torch.get_rng_state(),cuda_rng_states=torch.cuda.get_rng_state_all())
                latest_checkpoint=str(folder/f'update-{previous_updates+iteration+1}.pt')
            report=dict(config=vars(args),checkpoint=latest_checkpoint,latest_update=previous_updates+iteration+1,records=records,completed=False,
                experiment_initial_checkpoint=args.experiment_initial_checkpoint,source_snapshot=source_snapshot,
                resumed_from_updates=previous_updates,
                total_parameters=sum(p.numel() for p in pair.parameters()),trainable_parameters=sum(p.numel() for p in pair.parameters() if p.requires_grad),
                reward='Normal terminal win/loss +/-1, minus '+str(args.step_cost)+' per owned action; gamma-correct potential coefficient '+str(args.shaping)+'; artificial truncation bootstraps final observation',
                wall_seconds=time.monotonic()-started,source='Official v15 attacker/defender, frozen graph encoder, head-only PPO')
            atomic_json(args.output,report);print(record,flush=True)
        vector.close();vector=None
        report.update(completed=True,all_workers_exit_zero=True)
        atomic_json(args.output,report)
    finally:
        if vector:vector.abort()


if __name__=='__main__':
    from native_cuda_env import maybe_reexec
    maybe_reexec()
    main()
