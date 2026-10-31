"""Actual dcaab learner-boundary CPU restoration and nonmutating corruption checks."""
import argparse,collections,copy,json,random
from pathlib import Path
import numpy as np
import torch
import restore_learner as restore
HERE=Path(__file__).resolve().parent
def global_state():
    return dict(torch=torch.get_rng_state().clone(),python=random.getstate(),numpy=restore.numpy_state_payload())
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);model,opt,bundle,spec=restore.prepare()
    assert bundle['actual_Adam_steps']==3840 and bundle['completed_updates']==30 and bundle['environment_steps']==15360
    assert [len(g) for g in spec['named_parameter_groups']]==[32,162]
    assert len(spec['model_shapes'])==658 and len(spec['trainable_names'])==194
    # Deliberately damage live weights before restore, not the approved checkpoint.
    with torch.no_grad():next(model.parameters()).add_(.125)
    counter=restore.install_counter(opt,0)
    result=restore.restore_CPU(bundle,spec,model,opt,counter)
    assert restore.digest(model.state_dict())==restore.digest(restore.weight_state(bundle))
    assert restore.digest(opt.state_dict())==restore.digest(bundle['optimizer_state_dict'])
    assert restore.digest(global_state())==restore.digest(dict(torch=bundle['torch_rng_state'],python=bundle['python_rng_state'],numpy=bundle['numpy_rng_state']))
    assert counter['steps']==3840 and result['CUDA_restore_executed'] is False
    private_torch=torch.Generator(device='cpu');private_torch.set_state(bundle['torch_rng_state'])
    expected_torch=torch.rand(17,generator=private_torch)
    private_py=random.Random(1);private_py.setstate(bundle['python_rng_state']);expected_py=[private_py.random() for _ in range(9)]
    private_np=np.random.RandomState(1);private_np.set_state(restore.numpy_state_tuple(bundle['numpy_rng_state']));expected_np=private_np.rand(17)
    assert torch.equal(torch.rand(17),expected_torch) and [random.random() for _ in range(9)]==expected_py
    assert np.array_equal(np.random.rand(17),expected_np)
    rejected=[]
    def reject(name,mutate):
        bad=restore.clone(bundle);mutate(bad)
        before=restore.digest(dict(model=model.state_dict(),optimizer=opt.state_dict(),rng=global_state(),counter=counter))
        try:restore.restore_CPU(bad,spec,model,opt,counter)
        except (ValueError,TypeError,KeyError,RuntimeError,AssertionError) as error:rejected.append(dict(case=name,rejected=True,reason=str(error)))
        else:raise AssertionError('Corrupt boundary accepted '+name)
        assert restore.digest(dict(model=model.state_dict(),optimizer=opt.state_dict(),rng=global_state(),counter=counter))==before,name
    role='attacker';weight=next(iter(bundle['models'][role]['weights']))
    identity=bundle['optimizer_state_dict']['param_groups'][0]['params'][0]
    reject('partial_update',lambda b:b.update(complete_update_boundary=False))
    reject('wrong_mode',lambda b:b.update(finetuning_mode='heads'))
    reject('native_live_restore_claim',lambda b:b.update(native_environment_restorable=True))
    reject('counter_reset_to_zero',lambda b:b.update(actual_Adam_steps=0))
    reject('counter_drift',lambda b:b.update(actual_Adam_steps=3841))
    reject('wrong_role_graph_metadata',lambda b:b['models']['attacker']['metadata'].update(side='1'))
    reject('missing_model_parameter',lambda b:b['models'][role]['weights'].pop(weight))
    reject('NaN_model_weight',lambda b:b['models'][role]['weights'][weight].fill_(float('nan')))
    reject('finite_model_corruption',lambda b:b['models'][role]['weights'][weight].add_(.125))
    reject('wrong_Adam_learning_rate',lambda b:b['optimizer_state_dict']['param_groups'][0].update(lr=1e-3))
    reject('reordered_named_binding',lambda b:b['optimizer_state_dict']['param_groups'][0]['params'].reverse())
    reject('missing_Adam_moment',lambda b:b['optimizer_state_dict']['state'].pop(identity))
    reject('wrong_Adam_moment_shape',lambda b:b['optimizer_state_dict']['state'][identity].update(exp_avg=torch.zeros(2)))
    reject('NaN_Adam_moment',lambda b:b['optimizer_state_dict']['state'][identity]['exp_avg'].fill_(float('nan')))
    reject('malformed_CPU_RNG',lambda b:b.update(torch_rng_state=torch.zeros(3,dtype=torch.int64)))
    reject('missing_CUDA_payload',lambda b:b.update(cuda_rng_states=[]))
    reject('malformed_CUDA_payload',lambda b:b.update(cuda_rng_states=[torch.zeros(16)]))
    reject('malformed_Python_RNG',lambda b:b.update(python_rng_state=(3,(1,),None)))
    reject('malformed_NumPy_RNG',lambda b:b['numpy_rng_state'].update(position=625))
    oldsupport=HERE.parent/'battle-diverse-curriculum-20261020/support.py'
    trainer=HERE.parent/'battle-diverse-curriculum-20261020/train_last_graph.py'
    assert restore.sha(oldsupport)==bundle['frozen_inputs']['input_sha256'][str(oldsupport)]
    assert restore.sha(trainer)==bundle['frozen_inputs']['input_sha256'][str(trainer)]
    training=Path('/root/heroes3-ai-lab/evaluations/battle-diverse60-native-02/training.json')
    original=json.loads(training.read_text());assert original['completed'] and original['all_workers_exit_zero'] and original['checkpoint']==str(restore.DEFAULT_CHECKPOINT)
    steps=collections.Counter(int(v['step']) for v in bundle['optimizer_state_dict']['state'].values())
    report=dict(passed=True,actual_checkpoint_sha256=spec['checkpoint_sha256'],CPU_only=True,torch_version=str(torch.__version__),
        audit_optimizer_steps=0,new_native_games=0,GPU_restore_executed=False,CUDA_rng_payload_only=True,
        complete_saved_updates=30,saved_environment_steps=15360,actual_Adam_counter_restored=counter['steps'],
        actual_model_and_Adam_exact=True,torch_Python_NumPy_RNG_recovery_and_next_draws_exact=True,
        parameter_count=658,trainable_count=194,frozen_count=464,
        ordered_Adam_groups=[dict(name='heads' if i==0 else 'last_graph',count=len(names),lr=bundle['optimizer_state_dict']['param_groups'][i]['lr'],names=names) for i,names in enumerate(spec['named_parameter_groups'])],
        Adam_state_entries=len(bundle['optimizer_state_dict']['state']),per_parameter_step_counts=dict(steps),
        CUDA_payload_shapes=spec['CUDA_rng_shapes'],negative_cases=rejected,invalid_resume_preserves_model_Adam_RNG_counter=True,
        old_support_and_trainer_unchanged=True,native_environment_restored=False,old_workers_closed_in_training_report=True,
        new_explicit_schedule_and_epoch_required=True,next_schedule_phase=None,new_training_budget_selected=False,
        source_sha256={p.name:restore.sha(p) for p in HERE.glob('*.py')},frozen_graph_sources=spec['source_sha256'],
        original_training_report_sha256=restore.sha(training),limitation='Actual saved learner boundary restored on CPU. CUDA RNG was checked only as saved payload; no GPU replay, no live native-state restore, no new learning or ability claim.')
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    (a.out/'NAMED_BINDING.json').write_text(json.dumps(dict(named_parameter_groups=spec['named_parameter_groups'],shapes=spec['model_shapes'],trainable_names=spec['trainable_names']),indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='ordered_Adam_groups'},indent=2))
if __name__=='__main__':main()
