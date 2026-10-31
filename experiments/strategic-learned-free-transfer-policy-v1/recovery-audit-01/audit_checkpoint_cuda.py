import sys
from pathlib import Path
LOCAL=Path(__file__).resolve().parent
POLICY=LOCAL.parent
RUN=POLICY.parent/'strategic-learned-free-transfer-run-v1'
sys.path.insert(0,str(RUN));sys.path.insert(0,str(POLICY))
"""Independent exact model/Adam/global RNG recovery audit. No optimizer step."""
import argparse,copy,json,random
from pathlib import Path
import torch
from collect_episode_v5 import owned_resources,sha,write
from model_io import read,load_model,restore_training,tensor_sha,cpu_tree

def equal(a,b):
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and torch.equal(a.cpu(),b.cpu())
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b
def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--capsule',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--source-only',action='store_true');a=p.parse_args()
    bundle,digest=read(a.checkpoint)
    assert bundle['snapshot_device']=='cuda' and bundle['progress']['completed']
    assert all(sha(Path(f))==h for f,h in bundle['protocol']['sources'].items())
    assert all(sha(a.capsule/'bin'/n)==h for n,h in bundle['protocol']['native_artifacts'].items())
    assert sha(a.capsule/'build-source-manifest.json')==bundle['protocol']['capsule_manifest_sha256']
    assert bundle['schema']=='strategy-candidates-v5' and bundle['protocol']['economy_epoch']=='learned-economy-build-v1'
    if a.source_only:
        a.out.mkdir(parents=True,exist_ok=False)
        report=dict(source_review_passed=True,checkpoint_sha256=digest,format=bundle['format'],
            optimizer_steps_saved=bundle['optimizer_steps_total'],training_updates=bundle['training_updates'],
            all_protocol_sources_native_artifacts_unchanged=True,actual_CUDA_restore_executed=False,audit_optimizer_steps=0,
            auditor_sha256=sha(Path(__file__)))
        write(a.out/'AUDIT.json',report);print(json.dumps(report,indent=2));return
    with owned_resources():
        torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        model,loaded,read_sha=load_model(a.checkpoint,'cuda');optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
        update=restore_training(loaded,model,optimizer,protocol_sha=bundle['protocol_sha256'],device='cuda')
        assert update==bundle['training_updates'] and digest==read_sha
        assert tensor_sha(model.state_dict())==bundle['policy_tensor_sha256']
        assert equal(cpu_tree(optimizer.state_dict()),bundle['optimizer'])
        stop=optimizer.state[model.actor.stop_bias]
        assert stop['exp_avg'].device.type=='cuda' and int(stop['step'])>0 and float(stop['exp_avg'])!=0
        build=optimizer.state[model.actor.build_bias]
        assert build['exp_avg'].device.type=='cuda' and int(build['step'])>0
        assert float(model.actor.build_bias.detach().cpu())==bundle['prior_config']['build_bias']
        expected_cpu=torch.rand(17);expected_cuda=torch.rand(17,device='cuda').cpu();expected_python=[random.random() for _ in range(7)]
        torch.manual_seed(999);torch.cuda.manual_seed_all(999);random.seed(999)
        restore_training(loaded,model,optimizer,protocol_sha=bundle['protocol_sha256'],device='cuda')
        assert torch.equal(expected_cpu,torch.rand(17)) and torch.equal(expected_cuda,torch.rand(17,device='cuda').cpu())
        assert expected_python==[random.random() for _ in range(7)]
        rejected=[]
        for case in ['partial','protocol_change','adam_count','wrong_stop_moment','wrong_build_moment','cpu_as_cuda']:
            bad=copy.deepcopy(bundle);protocol_sha=bundle['protocol_sha256']
            if case=='partial':bad['complete_update_boundary']=False
            if case=='protocol_change':protocol_sha='0'*64
            if case=='adam_count':bad['optimizer_steps_total']+=1
            if case=='wrong_stop_moment':
                index=bad['parameter_groups'][0].index('actor.stop_bias');identity=bad['optimizer']['param_groups'][0]['params'][index]
                bad['optimizer']['state'][identity]['exp_avg']=torch.zeros(2)
            if case=='wrong_build_moment':
                index=bad['parameter_groups'][0].index('actor.build_bias');identity=bad['optimizer']['param_groups'][0]['params'][index]
                bad['optimizer']['state'][identity]['exp_avg']=torch.zeros(2)
            if case=='cpu_as_cuda':bad['snapshot_device']='cpu';bad['rng']['cuda']=[]
            before=tensor_sha(model.state_dict());opt_before=cpu_tree(optimizer.state_dict());rng_before=torch.get_rng_state().clone();cuda_before=torch.cuda.get_rng_state().clone();python_before=random.getstate()
            try:restore_training(bad,model,optimizer,protocol_sha=protocol_sha,device='cuda')
            except (ValueError,AssertionError):rejected.append(case)
            else:raise AssertionError('Invalid checkpoint resumed '+case)
            assert tensor_sha(model.state_dict())==before and equal(opt_before,cpu_tree(optimizer.state_dict()))
            assert torch.equal(rng_before,torch.get_rng_state()) and torch.equal(cuda_before,torch.cuda.get_rng_state())
            assert python_before==random.getstate()
    a.out.mkdir(parents=True,exist_ok=False)
    report=dict(passed_exact=True,checkpoint_sha256=digest,training_updates=update,optimizer_steps_restored=bundle['optimizer_steps_total'],
        model_Adam_stop_moment_exact=True,cpu_CUDA_python_RNG_exact=True,invalid_resume_does_not_mutate_state=True,
        negative_cases=rejected,audit_optimizer_steps=0,auditor_sha256=sha(Path(__file__)),
        build_bias_and_Adam_moment_exact=True,build_bias=float(model.actor.build_bias.detach().cpu()),
        limitation='Exact saved boundary recovery. Continuous-vs-split native training equivalence requires an additional experiment.')
    write(a.out/'AUDIT.json',report);print(json.dumps(report,indent=2))
if __name__=='__main__':main()


