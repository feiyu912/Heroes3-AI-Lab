"""Root-owned explicit CUDA learner restoration audit. Default is source/CPU inspection only."""
import argparse,collections,contextlib,fcntl,json,random
from pathlib import Path
import numpy as np
import torch
import restore_learner as restore
LAB=Path('/root/heroes3-ai-lab')
@contextlib.contextmanager
def leases():
    handles=[]
    try:
        for name in ('.gpu-learner-lock','.pool-lock'):
            h=(LAB/'evaluations'/name).open('a+');fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(h)
        yield
    finally:
        for h in reversed(handles):h.close()
def states(model,opt,counter):
    return restore.digest(dict(model=model.state_dict(),optimizer=opt.state_dict(),counter=counter,
        CPU=torch.get_rng_state(),CUDA=torch.cuda.get_rng_state_all(),python=random.getstate(),numpy=restore.numpy_state_payload()))
def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,default=restore.DEFAULT_CHECKPOINT);p.add_argument('--expected-sha',default=restore.DEFAULT_SHA)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
    a.out.mkdir(exist_ok=False,parents=True);torch.set_num_threads(1)
    model,opt,bundle,spec=restore.prepare(a.checkpoint,a.expected_sha)
    report=dict(checkpoint_sha256=spec['checkpoint_sha256'],source_inspection_passed=True,
        CUDA_restore_executed=False,audit_optimizer_steps=0,new_native_games=0,native_environment_restored=False,
        auditor_sha256=restore.sha(Path(__file__)),helper_sha256=restore.sha(Path(restore.__file__)))
    if not a.execute:
        report.update(plan_only=True,saved_actual_Adam_steps=bundle['actual_Adam_steps'],native_fresh_required=True)
    else:
        with leases():
            counter=restore.install_counter(opt,0);restore.restore_CPU(bundle,spec,model,opt,counter)
            model.cuda();restore.finalize_CUDA(bundle,spec,model,opt,counter)
            assert restore.digest(model.state_dict())==restore.digest(restore.weight_state(bundle))
            assert restore.digest(opt.state_dict())==restore.digest(bundle['optimizer_state_dict'])
            assert all(torch.equal(a.cpu(),b.cpu()) for a,b in zip(torch.cuda.get_rng_state_all(),bundle['cuda_rng_states']))
            expected_CPU=torch.rand(17);expected_CUDA=torch.rand(17,device='cuda').cpu();expected_Python=[random.random() for _ in range(7)];expected_NumPy=np.random.rand(17)
            torch.manual_seed(999);torch.cuda.manual_seed_all(999);random.seed(999);np.random.seed(999)
            restore.restore_global_rng(bundle,spec,cuda=True)
            assert torch.equal(expected_CPU,torch.rand(17)) and torch.equal(expected_CUDA,torch.rand(17,device='cuda').cpu())
            assert expected_Python==[random.random() for _ in range(7)] and np.array_equal(expected_NumPy,np.random.rand(17))
            rejected=[];identity=bundle['optimizer_state_dict']['param_groups'][0]['params'][0]
            for case in ('partial','wrong_mode','counter_reset','counter_drift','group_binding','moment_shape','CUDA_RNG','Python_RNG','NumPy_RNG'):
                bad=restore.clone(bundle)
                if case=='partial':bad['complete_update_boundary']=False
                if case=='wrong_mode':bad['finetuning_mode']='heads'
                if case=='counter_reset':bad['actual_Adam_steps']=0
                if case=='counter_drift':bad['actual_Adam_steps']+=1
                if case=='group_binding':bad['optimizer_state_dict']['param_groups'][0]['params'].reverse()
                if case=='moment_shape':bad['optimizer_state_dict']['state'][identity]['exp_avg']=torch.zeros(2)
                if case=='CUDA_RNG':bad['cuda_rng_states']=[]
                if case=='Python_RNG':bad['python_rng_state']=(3,(1,),None)
                if case=='NumPy_RNG':bad['numpy_rng_state']['position']=625
                before=states(model,opt,counter)
                try:restore.finalize_CUDA(bad,spec,model,opt,counter)
                except (ValueError,RuntimeError,AssertionError,TypeError,KeyError):rejected.append(case)
                else:raise AssertionError('Bad boundary accepted '+case)
                assert states(model,opt,counter)==before,case
            report.update(plan_only=False,passed_exact=True,CUDA_restore_executed=True,
                model_Adam_named_binding_exact=True,CPU_CUDA_Python_NumPy_RNG_exact=True,actual_Adam_counter_restored=counter['steps'],
                per_parameter_steps=dict(collections.Counter(int(v['step']) for v in opt.state.values())),
                invalid_resume_preserves_model_Adam_all_RNG_counter=True,negative_cases=rejected,
                native_fresh_required=True,new_schedule_epoch_required=True)
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
