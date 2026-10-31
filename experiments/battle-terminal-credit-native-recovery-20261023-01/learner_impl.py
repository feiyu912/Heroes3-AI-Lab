"""Explicit GPU/native entry point; invoked only by lease-owning controller."""
import argparse,copy,json,os,random,sys,time
from pathlib import Path
import numpy as np
import torch
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent.parent;R=ROOT/'research';LAB=Path('/root/heroes3-ai-lab');sys.path[:0]=[str(R),str(LAB/'src/gym')]
import full_graph_policy as graph
import decision_model
import restore_learner as restore
import legacy_support as support
import recorded_vector
import targets
import leases
from masked_ppo import gae,distribution,update
from lab_io import atomic_json
PARENT_SHA=restore.DEFAULT_SHA
def save(path,payload):
    path=Path(path);assert not path.exists();tmp=path.with_suffix('.tmp');torch.save(payload,tmp);os.replace(tmp,path)
    return dict(path=str(path),sha256=restore.sha(path),bytes=path.stat().st_size)
def verify(path):
    d=json.loads(Path(path).read_text());assert d['schema']=='terminal-drain-prefix-credit-v1' and all(restore.sha(p)==h for p,h in d['input_sha256'].items());return d
def resource():
    import shutil
    m={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())};disk=shutil.disk_usage(LAB)
    assert m['MemAvailable']>4*1024*1024 and m['SwapTotal']-m['SwapFree']<256*1024 and disk.free>10*1024**3
    return dict(available_mib=m['MemAvailable']/1024,swap_used_mib=(m['SwapTotal']-m['SwapFree'])/1024,disk_free_gib=disk.free/1024**3)
def post_update_resource():
    import subprocess
    m={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())}
    values=dict(available_mib=m['MemAvailable']/1024,swap_used_mib=(m['SwapTotal']-m['SwapFree'])/1024)
    # The approved post-update reserve is RAM>2 GiB. Swap is recorded, not a
    # stop condition here; the stricter pre-phase swap<256 MiB guard remains.
    assert m['MemAvailable']>2*1024*1024,f"Post-update RAM reserve failed: {values}"
    row=subprocess.check_output(['nvidia-smi','--query-gpu=temperature.gpu,memory.used','--format=csv,noheader,nounits'],text=True).splitlines()[0].split(',')
    assert float(row[0])<86 and float(row[1])<14000,f"Post-update GPU limit failed: {row}"
    values.update(gpu_temperature=float(row[0]),gpu_memory_mib=float(row[1]))
    return values
def configs(rows,run,phase):
    out=[]
    for row in rows:
        assert restore.sha(LAB/'data/vcmi/Maps'/row['map'])==row['map_sha256'] and row['scenario_index']<192
        role=row['role'];opponent=row['opponent'];out.append(dict(map=row['map'],role=role,opponent=opponent,initial_reset_once=True,
            opponent_model='DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx' if opponent=='MMAI_MODEL' else None,
            seed=row['seed'],feature_version='upstream-graph-v15',step_cost=0.,family=row['family'],TRAIN_scenario_index=row['scenario_index'],timeout=90,
            worker_root=str(LAB/'workers'/run/f'{phase}-{row["slot"]}')))
    return out
def global_rng():return restore.digest(dict(CPU=torch.get_rng_state(),CUDA=torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else [],Python=random.getstate(),NumPy=restore.numpy_state_payload()))
def collect(model,vector,current,count,folder,name,behavior_checkpoint,generators=None):
    arrays={k:[] for k in targets.KEYS};raw=dict(samples=[],actions=[],old_logp=[]);journal=[];start=time.monotonic();rng_before=global_rng()
    device=next(model.parameters()).device
    for tick in range(count):
        if generators:assert time.monotonic()-start<300,'Suffix wall-time cap (not loss)'
        with torch.inference_mode():
            batch=graph.collate(current,device);logits,value=model(*batch);dist=distribution(logits,batch[-1])
            chosen=dist.sample() if generators is None else torch.stack([torch.multinomial(dist.probs[i],1,generator=g).squeeze(0) for i,g in enumerate(generators)])
            logp=dist.log_prob(chosen);native=[int(o['active_action_ids'][a]) for o,a in zip(current,chosen.tolist())]
        decision=dict(schema='terminal-credit-decision-v1',phase_part=name,tick=tick,obs=copy.deepcopy(current),logits=logits.cpu(),probabilities=dist.probs.cpu(),values=value.cpu(),actions=chosen.cpu(),native_actions=native,loss_membership=not bool(generators))
        journal.append(save(folder/f'{name}-{tick:03d}-decision.pt',decision))
        transitions=vector.step(native)
        journal.append(save(folder/f'{name}-{tick:03d}-return.pt',dict(schema='terminal-credit-actual-vector-return-v1',responses=transitions)))
        next_obs=[x['features'] for x in transitions]
        with torch.inference_mode():
            _,nv=model(*graph.collate(next_obs,device));nv=nv.cpu().numpy().copy()
            for i,x in enumerate(transitions):
                if x['truncated'] and not x['terminated']:
                    _,v=model(*graph.collate([x['final_features']],device));nv[i]=float(v)
        shaped=[]
        for old,x in zip(current,transitions):
            nxt=0. if x['terminated'] else graph.potential(x['final_features'] if x['truncated'] else x['features'])
            shaped.append(x['reward']+.5*(nxt-graph.potential(old)))
        raw['samples'].extend(current);raw['actions'].extend(chosen.tolist());raw['old_logp'].extend(logp.tolist())
        for key,payload in dict(reward=shaped,value=value.cpu().numpy(),next_value=nv,terminal=[x['terminated'] for x in transitions],truncated=[x['truncated'] for x in transitions]).items():arrays[key].append(payload)
        current=next_obs
    arrays={k:np.asarray(v,np.bool_ if k in ['terminal','truncated'] else np.float32) for k,v in arrays.items()}
    if generators:assert rng_before==global_rng(),'Suffix changed global learner RNG'
    evidence=save(folder/(name+'.pt'),dict(arrays=arrays,raw=raw,journal=journal,suffix_private_RNG=bool(generators),behavior_checkpoint=str(behavior_checkpoint),behavior_checkpoint_sha256=restore.sha(behavior_checkpoint)))
    return current,arrays,raw,evidence
def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--expected-sha',required=True);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--arm',choices=['control','candidate'],required=True);p.add_argument('--phase-start',type=int,required=True);p.add_argument('--phase-stop',type=int,required=True);p.add_argument('--qualify',action='store_true');a=p.parse_args()
    lease_proof=leases.verify_pair();assert all(os.environ.get(k) in (None,'','0') for k in ['LAB_NATIVE_ONNX_CUDA','LAB_ONNX_CUDA','LAB_BATTLEAI_TEACHER'])
    assert 0<=a.phase_start<a.phase_stop<=4 and (not a.qualify or (a.phase_start,a.phase_stop)==(0,1));a.out.mkdir(parents=True,exist_ok=False)
    frozen=verify(a.freeze);torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    model,cpuopt,b,spec=restore.prepare(a.checkpoint,a.expected_sha);cpu_counter=restore.install_counter(cpuopt);proof=restore.restore_CPU(b,spec,model,cpuopt,cpu_counter);proof.pop('CUDA_rng_payload')
    assert b['completed_updates']==60+2*a.phase_start and b['environment_steps']==30720+1024*a.phase_start and b['actual_Adam_steps']==7680+256*a.phase_start
    if a.phase_start==0:assert a.expected_sha==PARENT_SHA
    else:assert b['terminal_credit_experiment']['arm']==a.arm and b['terminal_credit_experiment']['phase_complete'] and b['terminal_credit_experiment']['parent60_sha256']==PARENT_SHA
    assert [g['lr'] for g in cpuopt.param_groups]==[1e-5,1e-6]
    model.cuda().eval();opt=restore.optimizer_for(model,b);opt.load_state_dict(b['optimizer_state_dict']);counter=restore.install_counter(opt,b['actual_Adam_steps']);proof.update(restore.finalize_CUDA(b,spec,model,opt,counter));assert restore.live_named_groups(model,opt)==spec['named_parameter_groups']
    proof.update(checkpoint_sha256=a.expected_sha,full_named_Adam_exact=True,native_state_restored=False,resource_lease=lease_proof);atomic_json(a.out/'RESTORATION.json',proof)
    decision_model.collate=graph.collate
    registered=json.loads((HERE/'REGISTERED_CURRICULUM.json').read_text());records=[];vector=None;latest=str(a.checkpoint);total_suffix=1024*a.phase_start;total_native=2048*a.phase_start;admitted=1024*a.phase_start
    report=dict(passed=False,qualified=False,records=records,arm=a.arm,optimizer_steps_before=counter['steps'],inherited_Adam_steps=7680,qualify_only=a.qualify)
    try:
        for phase in range(a.phase_start,a.phase_stop):
            verify(a.freeze);resources=resource();folder=a.out/f'phase-{phase}';folder.mkdir();cfg=configs(registered['phases'][phase],a.out.name,phase);vector=recorded_vector.VectorEnv(cfg,executable=str(LAB/'venv/bin/python'));current=[x['features'] for x in vector.states]
            assert all(not x['torch_imported'] for x in vector.states),'Spawned native workers unexpectedly loaded Torch'
            atomic_json(folder/'WORKERS.json',dict(configs=cfg,worker_PIDs=[x['pid'] for x in vector.states],torch_imported=[x['torch_imported'] for x in vector.states]))
            if phase==a.phase_start:
                size,capacity=graph.choose_microbatch(model,current,8);assert size==8;atomic_json(a.out/'CAPACITY.json',capacity);restore.restore_global_rng(b,spec,cuda=True);assert all(support.restore_all_rng(b).values())
            generators=[torch.Generator(device='cuda').manual_seed(row['drain_sampling_seed']) for row in registered['phases'][phase]]
            phase_model_before=restore.digest(model.state_dict());phase_opt_before=restore.digest(opt.state_dict())
            for half in range(2):
                current,prefix,raw,evidence=collect(model,vector,current,32,folder,'admitted-'+str(half),latest);total_native+=512
                if half==1:
                    behavior_digest=restore.digest(model.state_dict());adam_digest=restore.digest(opt.state_dict());rng=global_rng()
                    private_rng_before=[g.get_state().cpu() for g in generators]
                    current,suffix,sraw,sevidence=collect(model,vector,current,64,folder,'suffix',latest,generators);total_suffix+=1024;total_native+=1024
                    assert behavior_digest==restore.digest(model.state_dict()) and adam_digest==restore.digest(opt.state_dict()) and rng==global_rng()
                    target=targets.build(prefix,suffix,a.arm);target_evidence=save(folder/'TARGETS.pt',dict(prefix=evidence,suffix=sevidence,targets=target,behavior_model_digest=behavior_digest,behavior_model_after_suffix=restore.digest(model.state_dict()),Adam_digest=adam_digest,Adam_after_suffix=restore.digest(opt.state_dict()),learning_RNG_before_suffix=rng,learning_RNG_after_suffix=global_rng(),private_sampling_RNG_before=private_rng_before,private_sampling_RNG_after=[g.get_state().cpu() for g in generators],global_RNG_unchanged=True))
                else:
                    adv,ret=gae(*(prefix[k] for k in targets.KEYS),gamma=1.,lam=.95);target=dict(advantage=adv,returns=ret)
                if a.qualify:continue
                before=counter['steps'];before_parameters=support.snapshot(model)
                metrics=update(model,opt,raw['samples'],raw['actions'],raw['old_logp'],prefix['value'].reshape(-1),target['advantage'].reshape(-1),target['returns'].reshape(-1),epochs=2,batch_size=8,entropy_coef=.005,target_kl=.02,recompute_atol=2e-4,recompute_rtol=0.,recompute_batch_size=16)
                admitted+=512;global_update=60+phase*2+half+1;delta=support.delta(model,before_parameters);latest=str(a.out/f'update-{global_update}.pt')
                metadata=dict(arm=a.arm,phase=phase,half=half,phase_complete=half==1,parent60_sha256=PARENT_SHA,admitted_stage_rows=admitted,suffix_stage_rows=total_suffix,total_native_stage_rows=total_native,registered_factor='terminal-drain-prefix-credit-extension',target_evidence=target_evidence if half==1 else None,prefix_rollout=evidence)
                model.save(latest,finetuning_mode='last',completed_updates=global_update,environment_steps=30720+admitted,config=dict(mode='last',**{k:str(v) if isinstance(v,Path) else v for k,v in vars(a).items()}),optimizer_state_dict=opt.state_dict(),torch_rng_state=torch.get_rng_state(),cuda_rng_states=torch.cuda.get_rng_state_all(),python_rng_state=random.getstate(),numpy_rng_state=support.numpy_rng(),actual_Adam_steps=counter['steps'],complete_update_boundary=True,frozen_inputs=frozen,native_environment_restorable=False,rollout_evidence=evidence,terminal_credit_experiment=metadata)
                readback=support.check_readback(latest,model,opt,graph,counter['steps']);record=dict(update=global_update,phase=phase,half=half,actual_Adam=counter['steps']-before,cumulative_Adam=counter['steps'],admitted_stage_rows=admitted,suffix_stage_rows=total_suffix,native_stage_rows=total_native,checkpoint=latest,checkpoint_sha256=restore.sha(latest),metrics=metrics,parameter_delta=delta,checkpoint_readback=readback,prefix=evidence,targets=target_evidence if half==1 else None,resources=post_update_resource());records.append(record);atomic_json(a.out/'PROGRESS.json',dict(records=records,latest=latest))
                assert record['actual_Adam']==128,'Optimizer-budget mismatch; preserve output, do not force extra steps'
            if a.qualify:
                assert phase_model_before==restore.digest(model.state_dict()) and phase_opt_before==restore.digest(opt.state_dict()) and counter['steps']==7680
                assert any(target['eligible']),'Fixed qualification has no extension; inconclusive, no reseed'
                assert np.max(np.abs(target['candidate_advantage']-target['base_advantage']))>1e-6,'Qualification observed no target change'
                report['qualification_targets']=target_evidence;report['qualification_prefix_observations']=1024;report['qualified']=True
            vector.close();vector=None;verify(a.freeze);report['resources']=resources
        report.update(passed=True,checkpoint=latest,checkpoint_sha256=restore.sha(latest),actual_Adam_steps=counter['steps'],new_Adam_steps=counter['steps']-b['actual_Adam_steps'],admitted_stage_rows=admitted,suffix_stage_rows=total_suffix,total_native_stage_rows=total_native,normal_workers_shutdown=True)
    except BaseException as error:report.update(error=repr(error),checkpoint=latest,actual_Adam_steps=counter['steps'],partial_native_not_restorable=True);raise
    finally:
        if vector:vector.abort()
        atomic_json(a.out/'RESULT.json',report)
if __name__=='__main__':main()
