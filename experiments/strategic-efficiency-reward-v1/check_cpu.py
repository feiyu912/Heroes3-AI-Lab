"""CPU forward/backward equivalence and rejection gates; never optimizer.step."""
import argparse,copy,importlib.util,inspect,json,sys,tempfile
from pathlib import Path
import torch
from targets import HERE,BASE,INITIAL_SHA,SCHEMA,EPOCH,FORMULA,sha,verify_targets,load_targets,learning_return,validate_derived_sample,read,write,native_day_evidence
import efficiency_ppo as new
spec=importlib.util.spec_from_file_location('_frozen_efficiency_control',BASE/'episode_balanced_ppo.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
from model_io import load_model
from load_admitted import load as original
def rejects(function):
    try:function()
    except (ValueError,AssertionError,KeyError):return True
    raise AssertionError('Invalid case accepted')
def main():
    p=argparse.ArgumentParser();p.add_argument('--targets',type=Path,required=True);p.add_argument('--initialize',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    assert sha(a.initialize)==INITIAL_SHA
    manifest=verify_targets(a.targets);control=[];treatment=[];source=[];episodes=[];control_episodes=[];treatment_episodes=[]
    for e in manifest['episodes']:
        directory=Path(e['admission_directory']);r,m,_=original(directory);source+=r;episodes+=m
        r,m,_=load_targets(directory,a.targets,'control',verified=manifest);control+=r;control_episodes+=m
        r,m,_=load_targets(directory,a.targets,'treatment',verified=manifest);treatment+=r;treatment_episodes+=m
    po=old.prepare_batch(source,'cpu',episodes=episodes);pn=new.prepare_batch(control,'cpu',episodes=control_episodes)
    assert po['metadata']==pn['metadata']
    tensor_keys=[k for k in po if k!='metadata'];assert all(torch.equal(po[k],pn[k]) for k in tensor_keys)
    assert all({k:v for k,v in b.items() if k not in ('native_reward','learning_target')}==a for a,b in zip(source,control))
    pt=new.prepare_batch(treatment,'cpu',episodes=treatment_episodes)
    model,_,_=load_model(a.initialize,'cpu');other=copy.deepcopy(model)
    totals=[{},{}]
    for network,implementation,rows,prepared,total in [(model,old,source,po,totals[0]),(other,new,control,pn,totals[1])]:
        for offset in range(0,len(rows),64):
            indices=list(range(offset,min(offset+64,len(rows))))
            terms=implementation.objective_terms(network,rows,prepared,'cpu',indices)
            for k,v in terms.items():total[k]=total.get(k,0.)+float(v.detach())*len(indices)/len(rows)
            (terms['loss']*len(indices)/len(rows)).backward()
    assert totals[0]==totals[1]
    gradient_count=0
    for (name,a_param),(b_name,b_param) in zip(model.named_parameters(),other.named_parameters()):
        assert name==b_name and ((a_param.grad is None and b_param.grad is None) or torch.equal(a_param.grad,b_param.grad)),name
        gradient_count+=a_param.grad is not None
    bad=copy.deepcopy(treatment[0]);bad['return']+=.001
    negative_cases=dict(formula=rejects(lambda:validate_derived_sample(bad)),negative_time=rejects(lambda:learning_return(1,-1,'treatment')),
        missing_terminal=rejects(lambda:learning_return(None,3,'treatment')),boolean_time=rejects(lambda:learning_return(1,True,'treatment')),
        old_prepare_rejects_treatment=rejects(lambda:old.prepare_batch(treatment,'cpu',episodes=treatment_episodes)))
    for name,mutation in [('schema',lambda s:s['learning_target'].update(schema='old')),('epoch',lambda s:s['learning_target'].update(epoch='old')),
                          ('evidence',lambda s:s['learning_target'].update(evidence_sha256='')),('day',lambda s:s['learning_target'].update(terminal_native_day=0)),
                          ('native_reward',lambda s:s['learning_target'].update(native_reward=.99))]:
        row=copy.deepcopy(treatment[0]);mutation(row);negative_cases[name]=rejects(lambda:new.prepare_batch([row],'cpu'))
    with tempfile.TemporaryDirectory(prefix='efficiency-cpu-negative-') as temp:
        folder=Path(temp)
        for name,mutation in [('missing_source',lambda m:m['sources'].pop(next(iter(m['sources'])))),
                              ('wrong_parent',lambda m:m.update(parent_sha256='0'*64)),
                              ('wrong_arms',lambda m:m.update(arms={})),
                              ('forged_calendar',lambda m:m['episodes'][0]['day_evidence'].update(terminal_native_day=99999)),
                              ('wrong_target',lambda m:m['episodes'][0]['targets'].update(treatment=.99))]:
            forged=copy.deepcopy(manifest);mutation(forged);write(folder/'TARGETS.json',forged)
            negative_cases[name]=rejects(lambda:verify_targets(folder))
    assert inspect.getsource(old.objective_terms)==inspect.getsource(new.objective_terms)
    assert inspect.getsource(old.ppo_update)==inspect.getsource(new.ppo_update)
    result=dict(passed=True,device='cpu',optimizer_steps=0,gpu_runs=0,native_runs=0,samples=len(source),episodes=len(episodes),
        control_prepare_tensors_bit_exact=True,control_metadata_exact=True,control_all_minibatch_objective_exact=True,
        control_full_batch_accumulated_gradients_bit_exact=True,gradient_tensors=gradient_count,objective=totals[0],negative_cases=negative_cases,
        objective_and_optimizer_loop_source_identical=True,standalone_row_validation_is_not_raw_authentication=True,
        source_sha256=manifest['sources'],targets_sha256=sha(a.targets/'TARGETS.json'),shared_batch_sha256=manifest['shared_batch_sha256'],
        episode_targets=[dict(episode_id=e['episode_id'],native_reward=e['native_reward'],first_day=e['day_evidence']['first_request_day'],terminal_day=e['day_evidence']['terminal_native_day'],targets=e['targets']) for e in manifest['episodes']])
    write(a.out,result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
