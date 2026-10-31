"""Actual CPU restoration + schedule/binding rejection; no CUDA/native calls."""
import argparse,ast,collections,json,random
from pathlib import Path
import numpy as np
import torch
import curriculum,restore_learner as restore,support
HERE=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    for path in HERE.glob('*.py'):ast.parse(path.read_text())
    model,opt,bundle,reference=restore.prepare()
    assert (bundle['completed_updates'],bundle['environment_steps'],bundle['actual_Adam_steps'])==(57,29184,7296)
    assert [g['lr'] for g in bundle['optimizer_state_dict']['param_groups']]==[1e-5,3e-6]
    assert bundle['continuation_parent_sha256']=='dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa'
    counter=restore.install_counter(opt)
    restored=restore.restore_CPU(bundle,reference,model,opt,counter);restored.pop('CUDA_rng_payload')
    assert support.equal(model.state_dict(),restore.weight_state(bundle)) and support.equal(opt.state_dict(),bundle['optimizer_state_dict']) and counter['steps']==7296
    assert torch.equal(torch.get_rng_state(),bundle['torch_rng_state']) and random.getstate()==bundle['python_rng_state'] and restore.numpy_state_payload()==bundle['numpy_rng_state']
    def state():return restore.digest(dict(model=model.state_dict(),opt=opt.state_dict(),counter=counter,torch=torch.get_rng_state(),python=random.getstate(),numpy=restore.numpy_state_payload()))
    rejected=[];identity=bundle['optimizer_state_dict']['param_groups'][0]['params'][0]
    for case in ['partial','counter_reset','binding','moment_shape','CUDA_RNG','Python_RNG','NumPy_RNG']:
        bad=restore.clone(bundle)
        if case=='partial':bad['complete_update_boundary']=False
        if case=='counter_reset':bad['actual_Adam_steps']=0
        if case=='binding':bad['optimizer_state_dict']['param_groups'][0]['params'].reverse()
        if case=='moment_shape':bad['optimizer_state_dict']['state'][identity]['exp_avg']=torch.zeros(2)
        if case=='CUDA_RNG':bad['cuda_rng_states']=[]
        if case=='Python_RNG':bad['python_rng_state']=(3,(1,),None)
        if case=='NumPy_RNG':bad['numpy_rng_state']['position']=625
        before=state()
        try:restore.restore_CPU(bad,reference,model,opt,counter)
        except (ValueError,AssertionError,RuntimeError,TypeError,KeyError):rejected.append(case)
        else:raise AssertionError('Invalid boundary accepted '+case)
        assert state()==before
    phases=[13,14,14];configs=[curriculum.configs(HERE.parent.parent/'research/diverse-curriculum.json',2026102016,phase,'cpu-check') for phase in phases]
    assert len(configs[0])==16 and configs[1]==configs[2]
    assert [c['seed'] for c in configs[0]]==list(range(2026118800,2026118816))
    assert [c['seed'] for c in configs[1]]==list(range(2026117800,2026117816))
    pause=json.loads((HERE.parent/'battle-training-continuation-20261020/monitor-independent-01/user-pause-01/PAUSE.json').read_text())
    for arm in ['candidate','control']:
        item=pause['saved'][arm];assert restore.sha(item['checkpoint'])==item['sha256'] and restore.sha(item['copy'])==item['sha256']
    report=dict(passed=True,CPU_model_Adam_Python_NumPy_Torch_RNG_exact=True,CUDA_payload_validated_only=True,CUDA_restore_executed=False,
        no_native_games=True,audit_Adam_steps=0,checkpoint_sha256=reference['checkpoint_sha256'],restored=restored,negative_cases=rejected,
        invalid_boundaries_preserve_live_state=True,phase_schedule=phases,fresh_phase13_seeds=[c['seed'] for c in configs[0]],
        per_parameter_steps=dict(collections.Counter(int(v['step']) for v in opt.state.values())),source_sha256={str(x):restore.sha(x) for x in HERE.glob('*.py')})
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
