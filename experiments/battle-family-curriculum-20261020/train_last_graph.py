"""Fine-tune public typed graphs on varied armies with masked PPO and shaping."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np


def main():
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
    import torch
    from vector_env import VectorEnv
    import decision_model
    import support
    import curriculum
    import full_graph_policy as graph
    from masked_ppo import gae,distribution,update
    from lab_io import atomic_json,capture_source
    r=Path('/mnt/g/Heroes3-AI-Lab/research')
    p=argparse.ArgumentParser()
    p.add_argument('--checkpoint',required=True);p.add_argument('--output',required=True)
    p.add_argument('--models-dir',required=True);p.add_argument('--freeze',required=True)
    p.add_argument('--mode',choices=['heads','last','all'],default='last')
    p.add_argument('--workers',type=int,default=24);p.add_argument('--updates',type=int,default=128)
    p.add_argument('--rollout',type=int,default=32);p.add_argument('--microbatch',type=int,default=4)
    p.add_argument('--epochs',type=int,default=2);p.add_argument('--seed',type=int,default=20261020)
    p.add_argument('--learning-rate',type=float,default=1e-5)
    p.add_argument('--head-learning-rate',type=float,default=5e-5)
    p.add_argument('--opponents',nargs='+',default=['BattleAI','MMAI_MODEL'])
    p.add_argument('--scenario-file',default=str(r/'diverse-curriculum.json'))
    p.add_argument('--shaping',type=float,default=.5);p.add_argument('--step-cost',type=float,default=.002)
    p.add_argument('--gamma',type=float,default=.99);p.add_argument('--gae-lambda',type=float,default=.95)
    p.add_argument('--entropy-coef',type=float,default=.005)
    p.add_argument('--resume',action='store_true');p.add_argument('--rotate-every',type=int,default=16)
    p.add_argument('--native-opponent-device',choices=['cpu','cuda'],default='cuda' if os.environ.get('LAB_NATIVE_ONNX_CUDA')=='1' else 'cpu')
    p.add_argument('--no-auto-microbatch',action='store_true')
    p.add_argument('--experiment-initial-checkpoint')
    p.add_argument('--first-battle',action='store_true')
    args=p.parse_args()
    support.validate_args(args)
    frozen=support.verify_freeze(args.freeze)
    assert 0<args.gamma<=1 and 0<=args.gae_lambda<=1 and 0<=args.entropy_coef<=.1
    if not args.experiment_initial_checkpoint:args.experiment_initial_checkpoint=args.checkpoint
    assert json.loads((r/'full-graph-contract.json').read_text())['passed']
    torch.set_num_threads(2);torch.manual_seed(args.seed)
    __import__('random').seed(args.seed);np.random.seed(args.seed)
    # Atomic scatter sums vary even on the same raw graph. Deterministic kernels
    # plus rollout-shaped recomputation test the stored policy without changing
    # the optimizer minibatch or relaxing its probability tolerance.
    torch.use_deterministic_algorithms(True)
    args.deterministic_cuda=True;args.recompute_batch_size=args.workers
    model=graph.FullGraphPair(args.checkpoint,args.mode).cuda().eval()
    from gpu_opponent import configure_training,OpponentVector
    fixed_opponent=None  # Only actual native BattleAI/original public CPU ONNX opponents.
    decision_model.collate=graph.collate
    body=[];heads=[]
    for name,parameter in model.named_parameters():
        if parameter.requires_grad:
            (heads if 'policy_head__' in name or 'value_head__' in name else body).append(parameter)
    groups=[dict(params=heads,lr=args.head_learning_rate)]
    if body:groups.append(dict(params=body,lr=args.learning_rate))
    optimizer=torch.optim.Adam(groups)
    counter=support.install_step_counter(optimizer)
    initial_parameters=support.snapshot(model)
    previous=steps=0
    if args.resume:
        state=torch.load(args.checkpoint,map_location='cpu',weights_only=True)
        assert state['finetuning_mode']==args.mode
        optimizer.load_state_dict(state['optimizer_state_dict'])
        torch.set_rng_state(state['torch_rng_state']);torch.cuda.set_rng_state_all(state['cuda_rng_states'])
        previous=state['completed_updates'];steps=state['environment_steps']
    cases=[c for c in json.loads(Path(args.scenario_file).read_text()) if c['split']=='train']
    run=str(time.time_ns());folder=Path(args.models_dir)/run
    source_snapshot=capture_source(folder,'train-graph-finetune.py')
    support.capture_local(folder,frozen)
    started=time.monotonic();records=[];episodes=wins=cuts=0;vector=None
    phase_close_events=[];live_steps=[]
    latest=str(args.checkpoint)
    try:
        for iteration in range(args.updates):
            if iteration%args.rotate_every==0:
                if vector:
                    phase_close_events.append(curriculum.close_evidence(phase,live_steps,configs,'phase_switch'))
                    vector.close();vector=None
                phase=(previous+iteration)//args.rotate_every
                curriculum.resource_gate()
                configs=curriculum.configs(args.scenario_file,args.seed,phase,run)
                live_steps=[0]*args.workers
                vector=(OpponentVector(configs,'/root/heroes3-ai-lab/venv/bin/python',fixed_opponent) if fixed_opponent
                        else VectorEnv(configs,executable='/root/heroes3-ai-lab/venv/bin/python'))
                current=[s['features'] for s in vector.states]
                if iteration==0:
                    # Tiny microbatches waste most of this GPU on launch overhead.
                    # Measure safe larger batches before any optimizer update.
                    args.requested_microbatch=args.microbatch
                    preferred=args.microbatch if args.no_auto_microbatch else max(args.microbatch,32 if args.mode!='all' else 16)
                    args.microbatch,capacity=graph.choose_microbatch(model,current,preferred)
                    capacity['selected_microbatch']=args.microbatch
                    atomic_json(Path(args.output).with_suffix('.microbatch.json'),capacity)
                    print('Verified graph microbatch capacity',capacity,flush=True)
            support.verify_freeze(args.freeze)
            before_parameters=support.snapshot(model)
            step_before=counter['steps']
            tick=time.monotonic();samples=[];actions=[];old_logp=[];values=[];next_values=[];rewards=[];terminated=[];truncated=[]
            timings=dict(inference=0.,environment=0.,update=0.)
            for _ in range(args.rollout):
                stamp=time.monotonic()
                with torch.inference_mode():
                    batch=graph.collate(current,'cuda');logits,value=model(*batch)
                    dist=distribution(logits,batch[-1]);chosen=dist.sample();logp=dist.log_prob(chosen)
                timings['inference']+=time.monotonic()-stamp
                samples.extend(current);actions.extend(chosen.tolist());old_logp.extend(logp.tolist());values.append(value.cpu().numpy())
                stamp=time.monotonic()
                transitions=vector.step([int(obs['active_action_ids'][a]) for obs,a in zip(current,chosen.tolist())])
                timings['environment']+=time.monotonic()-stamp
                next_obs=[s['features'] for s in transitions]
                with torch.inference_mode():
                    _,nv=model(*graph.collate(next_obs,'cuda'));nv=nv.cpu().numpy().copy()
                    for i,s in enumerate(transitions):
                        if s['truncated'] and not s['terminated']:
                            _,v=model(*graph.collate([s['final_features']],'cuda'));nv[i]=float(v)
                shaped=[]
                for old,s in zip(current,transitions):
                    nxt=0. if s['terminated'] else graph.potential(s['final_features'] if s['truncated'] else s['features'])
                    shaped.append(s['reward']+args.shaping*(args.gamma*nxt-graph.potential(old)))
                for worker,s in enumerate(transitions):
                    live_steps[worker]+=1
                    if s['terminated'] or s['truncated']:live_steps[worker]=0
                current=next_obs
                next_values.append(nv);rewards.append(shaped)
                terminated.append([s['terminated'] for s in transitions]);truncated.append([s['truncated'] for s in transitions])
                episodes+=sum(s['terminated'] for s in transitions)
                wins+=sum(s['terminated'] and s['outcome']['winner']==int(config['role']=='defender') for s,config in zip(transitions,configs))
                cuts+=sum(s['truncated'] and not s['terminated'] for s in transitions)
            advantage,returns=gae(rewards,values,next_values,terminated,truncated,gamma=args.gamma,lam=args.gae_lambda)
            support.save_rollout(folder,previous+iteration+1,dict(samples=samples,actions=actions,old_logp=old_logp,values=values,next_values=next_values,rewards=rewards,terminated=terminated,truncated=truncated,configs=configs))
            stamp=time.monotonic()
            metrics=update(model,optimizer,samples,actions,old_logp,np.asarray(values).reshape(-1),advantage.reshape(-1),returns.reshape(-1),
                epochs=args.epochs,batch_size=args.microbatch,entropy_coef=args.entropy_coef,target_kl=.02,
                recompute_atol=2e-4,recompute_rtol=0.,recompute_batch_size=args.workers)
            timings['update']=time.monotonic()-stamp
            assert counter['steps']>step_before,'No actual Adam step'
            parameter_delta=support.delta(model,before_parameters)
            support.verify_freeze(args.freeze)
            assert cuts<=max(2,episodes*.05),'Excessive truncations'
            mem={k:int(v.strip().split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
            assert mem['MemAvailable']>2*1024*1024 and mem['SwapTotal']-mem['SwapFree']<256*1024,'Memory reserve exceeded'
            record=dict(update=previous+iteration+1,samples=len(samples),steps_per_second=len(samples)/(time.monotonic()-tick),
                episodes=episodes,wins=wins,truncations=cuts,metrics=metrics,timing_seconds=timings,
                free_mib=mem['MemAvailable']/1024,gpu_peak_mib=torch.cuda.max_memory_allocated()/1024**2)
            record.update(actual_Adam_steps=counter['steps']-step_before,actual_Adam_steps_total=counter['steps'],parameter_delta=parameter_delta,delta_from_B64=support.delta(model,initial_parameters))
            records.append(record)
            if fixed_opponent:
                fixed_opponent.assert_unchanged()
                record['fixed_opponent']=dict(requests=fixed_opponent.requests,batches=fixed_opponent.batches,
                    inference_seconds=fixed_opponent.seconds,weights_unchanged=True)
            if iteration%16==0:
                telemetry=subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu,memory.used,utilization.gpu','--format=csv,noheader,nounits'],text=True).splitlines()[0].split(',')
                record['gpu_telemetry']=dict(zip(['temperature_c','memory_mib','utilization_percent'],[float(v.strip()) for v in telemetry]))
                assert record['gpu_telemetry']['temperature_c']<86 and record['gpu_telemetry']['memory_mib']<14000
            if True:  # Save every completed update, including short finite pilots.
                latest=str(folder/f'update-{previous+iteration+1}.pt')
                model.save(latest,finetuning_mode=args.mode,completed_updates=previous+iteration+1,
                    environment_steps=steps+(iteration+1)*args.workers*args.rollout,config=vars(args),
                    optimizer_state_dict=optimizer.state_dict(),torch_rng_state=torch.get_rng_state(),cuda_rng_states=torch.cuda.get_rng_state_all(),
                    python_rng_state=__import__('random').getstate(),numpy_rng_state=support.numpy_rng(),
                    actual_Adam_steps=counter['steps'],complete_update_boundary=True,frozen_inputs=frozen,
                    native_environment_restorable=False,phase_close_events=phase_close_events)
                record['checkpoint_readback']=support.check_readback(latest,model,optimizer,graph,counter['steps'])
                record['checkpoint_sha256']=support.sha(latest)
            report=dict(config=vars(args),checkpoint=latest,completed=False,resumed_from_updates=previous,
                experiment_initial_checkpoint=args.experiment_initial_checkpoint,source_snapshot=source_snapshot,
                records=records,phase_close_events=phase_close_events,wall_seconds=time.monotonic()-started,policy='recovered',
                total_parameters=sum(p.numel() for p in model.parameters()),trainable_parameters=sum(p.numel() for p in model.parameters() if p.requires_grad),
                reward='Normal terminal +/-1, step cost, gamma-correct army-value potential with zero terminal potential',
                CUDA_training=True)
            atomic_json(args.output,report);print(record,flush=True)
        phase_close_events.append(curriculum.close_evidence(phase,live_steps,configs,'final_budget_stop'))
        vector.close();vector=None
        report.update(completed=True,all_workers_exit_zero=True,phase_close_events=phase_close_events)
        atomic_json(args.output,report)
    except BaseException as error:
        atomic_json(args.output,dict(completed=False,error=repr(error),actual_Adam_steps=counter['steps'],
            CUDA_training=counter['steps']>0,checkpoint=latest,checkpoint_exists=Path(latest).is_file(),records=records,
            source_snapshot=source_snapshot,partial_live_state_not_resumable=True,config=vars(args),phase_close_events=phase_close_events))
        raise
    finally:
        if vector:vector.abort()


if __name__=='__main__':
    from native_cuda_env import maybe_reexec
    maybe_reexec()
    main()
