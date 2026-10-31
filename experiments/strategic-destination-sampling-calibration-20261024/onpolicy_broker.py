"""One CUDA policy sampler, no optimizer. Requires inherited exclusive GPU+pool leases."""
import argparse,base64,fcntl,hashlib,importlib.util,json,os,signal,sys,time
from pathlib import Path
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
LOCAL=Path(__file__).resolve().parent;HERE=LOCAL.parent/'strategic-active-opponent-policy-v4';TYPED=HERE;LAB=Path('/root/heroes3-ai-lab')
sys.path.append(str(HERE))
from movement_exploration import effective_distribution,TEMPERATURE,EPOCH
spec=importlib.util.spec_from_file_location('_typed_onpolicy_wire',TYPED/'broker.py')
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)

def verify_lease(fd,name):
    target=LAB/'evaluations'/name;stat=os.fstat(fd);identity=(stat.st_dev,stat.st_ino)
    assert identity==(target.stat().st_dev,target.stat().st_ino),'Inherited lease identity differs'
    with target.open('a') as probe:
        try:fcntl.flock(probe,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:pass
        else:raise RuntimeError('Exclusive parent resource lease missing')
    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    return dict(fd=fd,device=stat.st_dev,inode=stat.st_ino)

class OnPolicyBroker(wire.Broker):
    def __init__(self,checkpoint,sampling_seed):
        import torch
        torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
        torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        from model_io import load_model
        self.mode='new-policy';self.diagnostic_action=None
        self.model,_,self.model_sha256=load_model(checkpoint,'cuda')
        self.generator=torch.Generator(device='cuda').manual_seed(sampling_seed)
        self.initial_state=self.generator.get_state().clone();self.choices=0

    def propose(self,raw,expected_id):
        import torch
        request=wire.encoder.validate(json.loads(raw),expected_id)
        offered=[c['creature_id'] for c in request['candidates'] if c['op']=='recruit']
        if offered:wire.encoder.catalog_coverage(wire.encoder.active_catalog(),offered)
        assert all(type(request[k]) is int for k in ['player','hero'])
        with torch.no_grad():
            logits,values=self.model(**wire.encoder.collate([request],'cuda'))
            legal=logits[0,:len(request['candidates'])]
            assert bool(torch.isfinite(legal).all()) and bool(torch.isfinite(values).all())
            effective,raw_logp,logp,raw_mass,effective_mass=effective_distribution(legal,request['candidates'],TEMPERATURE)
            index=int(torch.multinomial(logp.exp(),1,generator=self.generator).item())
            old_logprob=float(logp[index]);value=float(values[0])
        response=dict(schema=wire.RESPONSE_SCHEMA,selected_index=index,decision_id=request['request_id'],player=request['player'],
            hero=request['hero'],own_turn=request['own_turn'],op=request['candidates'][index]['op'],request_sha256=wire.digest(raw),classification='new_policy')
        wire.validate_response(response,request,raw);self.choices+=1
        build_indices=[i for i,c in enumerate(request['candidates']) if c['op']=='build']
        recruit_indices=[i for i,c in enumerate(request['candidates']) if c['op']=='recruit']
        return dict(response=response,request=request,request_sha256=wire.digest(raw),model_sha256=self.model_sha256,
                    value=value,old_value=value,old_logprob=old_logprob,action=index,device='cuda',sampling='torch.multinomial_generator',
                    build_candidate_count=len(build_indices),build_probability=float(logp.exp()[build_indices].sum()) if build_indices else 0.,
                    recruit_candidate_count=len(recruit_indices),recruit_probability=float(logp.exp()[recruit_indices].sum()) if recruit_indices else 0.,
                    raw_logits=legal.detach().cpu().tolist(),effective_logits=effective.detach().cpu().tolist(),
                    raw_probabilities=raw_logp.exp().detach().cpu().tolist(),effective_probabilities=logp.exp().detach().cpu().tolist(),
                    raw_operation_probabilities={k:float(v) for k,v in raw_mass.items()},
                    effective_operation_probabilities={k:float(v) for k,v in effective_mass.items()},
                    distribution_epoch=EPOCH,move_temperature=TEMPERATURE,manual_exploration_setting=True,
                    manual_setting_is_learning=False,diagnostic_only=True,new_PPO_admissions=0,
                    economy_epoch=wire.encoder.EPOCH,
                    execution_verified=False,ppo_sample_admitted=False,native_request_id_assignment='pending_real_requestSent')

def main():
    p=argparse.ArgumentParser();p.add_argument('--agent-dir',type=Path,required=True);p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--sampling-seed',type=int,required=True);p.add_argument('--gpu-lock-fd',type=int,required=True);p.add_argument('--pool-lock-fd',type=int,required=True)
    p.add_argument('--idle-seconds',type=float,default=150);a=p.parse_args()
    leases={n:verify_lease(fd,n) for n,fd in [('.gpu-learner-lock',a.gpu_lock_fd),('.pool-lock',a.pool_lock_fd)]}
    a.agent_dir.mkdir(parents=True,exist_ok=True)
    with (a.agent_dir/'typed-broker.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        broker=OnPolicyBroker(a.checkpoint,a.sampling_seed);stopping=False
        def stop(*_):
            nonlocal stopping
            stopping=True
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        wire.atomic(a.agent_dir/'broker-ready.json',(json.dumps(dict(mode='onpolicy_cuda_move_temperature_v1',device='cuda',model_sha256=broker.model_sha256,
            optimizer_steps=0,sampling_seed=a.sampling_seed,leases=leases))+'\n').encode())
        number=1;last=time.monotonic()
        try:
            while not stopping:
                request=a.agent_dir/f'request-{number:08d}.json'
                if request.exists():
                    broker.process(request,number);number+=1;last=time.monotonic()
                elif time.monotonic()-last>a.idle_seconds:raise TimeoutError('On-policy sampler idle timeout')
                else:time.sleep(.005)
        finally:
            import torch
            state=dict(schema='strategic-move-temperature-calibration-sampling-state-v1',distribution_epoch=EPOCH,move_temperature=TEMPERATURE,manual_exploration_setting=True,manual_setting_is_learning=False,new_PPO_admissions=0,sampling_seed=a.sampling_seed,decisions=broker.choices,
                initial_state=broker.initial_state.cpu(),final_state=broker.generator.get_state().cpu(),
                checkpoint_sha256=broker.model_sha256,optimizer_steps=0,device='cuda')
            path=a.agent_dir/'sampling-state.pt';temporary=path.with_suffix('.pt.tmp')
            with temporary.open('wb') as stream:torch.save(state,stream);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,path)
    return 0
if __name__=='__main__':raise SystemExit(main())



