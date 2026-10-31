"""Independent actual schema6 boundary restore; no optimizer step or native game."""
import argparse,copy,hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
POLICY=ROOT/'experiments/strategic-learned-recruitment-policy-v2'
RUN=ROOT/'experiments/strategic-learned-recruitment-run-v1'
sys.path.insert(0,str(RUN));sys.path.insert(0,str(POLICY))
import torch
from collect_episode_v5 import owned_resources
from qualification import require_qualification
from model_io import read,load_model,restore_training,tensor_sha,cpu_tree

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def same(a,b):
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and torch.equal(a.cpu(),b.cpu())
    if isinstance(a,dict):return isinstance(b,dict) and a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return type(a)==type(b) and len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b
def snapshot(model,opt):
    return dict(model=cpu_tree(model.state_dict()),Adam=cpu_tree(opt.state_dict()),torch=torch.get_rng_state().clone(),
        CUDA=[x.cpu().clone() for x in torch.cuda.get_rng_state_all()],python=random.getstate())
def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    bundle,digest=read(a.checkpoint);binding=require_qualification();capsule=Path(binding['capsule_directory'])
    assert bundle['schema']=='strategy-candidates-v6' and bundle['snapshot_device']=='cuda' and bundle['progress']['completed']
    assert bundle['catalog_sha256']==binding['catalog_sha256']
    frozen=bundle['protocol']['sources']
    assert all(sha(path)==h for path,h in frozen.items())
    assert all(sha(capsule/'bin'/n)==h for n,h in bundle['protocol']['native_artifacts'].items())
    assert sha(capsule/'build-source-manifest.json')==bundle['protocol']['capsule_manifest_sha256']
    report=dict(passed_exact=False,checkpoint_sha256=digest,auditor_sha256=sha(__file__),audit_optimizer_steps=0,new_native_games=0)
    try:
        with owned_resources():
            torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            model,loaded,loadedsha=load_model(a.checkpoint,'cuda');opt=torch.optim.Adam(model.parameters(),lr=3e-4)
            update=restore_training(loaded,model,opt,protocol_sha=bundle['protocol_sha256'],device='cuda')
            assert loadedsha==digest and update==bundle['training_updates']
            assert tensor_sha(model.state_dict())==bundle['policy_tensor_sha256'] and same(cpu_tree(opt.state_dict()),bundle['optimizer'])
            new_names=['actor.recruit_bias','recruit_actor.weight','recruit_critic.weight'];actual={}
            for name in new_names:
                parameter=dict(model.named_parameters())[name];state=opt.state[parameter]
                assert state['exp_avg'].device.type=='cuda' and int(state['step'])>0
                actual[name]=dict(Adam_step=int(state['step']),moment_norm=float(state['exp_avg'].norm().cpu()),parameter_norm=float(parameter.detach().norm().cpu()))
            expected=(torch.rand(17),torch.rand(17,device='cuda').cpu(),[random.random() for _ in range(7)])
            torch.manual_seed(999);torch.cuda.manual_seed_all(999);random.seed(999)
            restore_training(loaded,model,opt,protocol_sha=bundle['protocol_sha256'],device='cuda')
            assert torch.equal(expected[0],torch.rand(17)) and torch.equal(expected[1],torch.rand(17,device='cuda').cpu())
            assert expected[2]==[random.random() for _ in range(7)]
            rejected=[]
            cases=['partial','protocol','counter','bad_CPU_RNG','bad_CUDA_RNG','bad_Python_RNG','wrong_LR','parameter_order','cpu_as_cuda']+['moment:'+n for n in new_names]
            for case in cases:
                bad=copy.deepcopy(bundle);protocol=bundle['protocol_sha256']
                if case=='partial':bad['complete_update_boundary']=False
                elif case=='protocol':protocol='0'*64
                elif case=='counter':bad['optimizer_steps_total']+=1
                elif case=='bad_CPU_RNG':bad['rng']['torch']=torch.zeros(3,dtype=torch.uint8)
                elif case=='bad_CUDA_RNG':bad['rng']['cuda']=[]
                elif case=='bad_Python_RNG':bad['rng']['python']=(3,(1,),None)
                elif case=='wrong_LR':bad['optimizer']['param_groups'][0]['lr']*=2
                elif case=='parameter_order':bad['parameter_groups'][0].reverse()
                elif case=='cpu_as_cuda':bad['snapshot_device']='cpu';bad['rng']['cuda']=[]
                elif case.startswith('moment:'):
                    name=case.split(':',1)[1]
                    for names,group in zip(bad['parameter_groups'],bad['optimizer']['param_groups']):
                        if name in names:
                            identity=group['params'][names.index(name)];bad['optimizer']['state'][identity]['exp_avg']=torch.zeros(2)
                before=snapshot(model,opt)
                try:restore_training(bad,model,opt,protocol_sha=protocol,device='cuda')
                except (ValueError,RuntimeError,AssertionError,TypeError,KeyError):rejected.append(case)
                else:raise AssertionError('Invalid state accepted: '+case)
                assert same(before,snapshot(model,opt)),'Rejected resume mutated live state: '+case
            assert all(sha(path)==h for path,h in frozen.items()) and sha(a.checkpoint)==digest
            report.update(passed_exact=True,actual_CUDA_restore_executed=True,model_Adam_exact=True,cpu_CUDA_python_RNG_exact=True,
                invalid_resume_does_not_mutate_state=True,negative_cases=rejected,training_updates=update,
                optimizer_steps_restored=bundle['optimizer_steps_total'],new_recruitment_parameters=actual,
                catalog_sha256=binding['catalog_sha256'],source_inputs_unchanged=True,
                limitation='Restores saved learner boundary, not in-flight native state or ability improvement.')
    except BaseException as e:
        report['error']=repr(e);raise
    finally:
        (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
