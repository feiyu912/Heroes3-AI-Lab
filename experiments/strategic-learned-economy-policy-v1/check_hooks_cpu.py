"""Synthetic codec/wire/objective checks; no CPU optimizer steps, native games or CUDA."""
import argparse,ast,copy,hashlib,json
from pathlib import Path
import torch
import broker,encoder,episode_balanced_ppo as ppo,model_io
from check_cpu import fixture
from migrate import migrate
HERE=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
    torch.set_num_threads(1);_,model,initial=migrate();r=fixture();raw=json.dumps(r).encode()
    response=dict(schema=broker.RESPONSE_SCHEMA,selected_index=2,decision_id=1,player=0,hero=0,own_turn=1,
        op='build',request_sha256=broker.digest(raw),classification='diagnostic_only')
    broker.validate_response(response,r,raw);rejects=[]
    for key,value in [('schema','strategy-typed-action-response-v1'),('selected_index',True),('decision_id',2),('player',1),('hero',2),('own_turn',2),('op','move'),('request_sha256','0'*64),('classification','expert')]:
        bad=dict(response);bad[key]=value
        try:broker.validate_response(bad,r,raw)
        except ValueError:rejects.append('response_'+key)
        else:raise AssertionError(key)
    logits,values=model(**encoder.collate([r]));samples=[]
    for i,action in enumerate((2,0)):
        samples.append(dict(episode_id='synthetic-'+str(i),valid=True,execution_verified=True,native_request_id=i+1,
            decision_id=1,policy_sha256='0'*64,request=copy.deepcopy(r),action=action,action_type=r['candidates'][action]['op'],
            old_logprob=float(logits.log_softmax(-1)[0,action].detach()),old_value=float(values[0].detach()),**{'return':(-1.,1.)[i]}))
    prepared=ppo.prepare_batch(samples);terms=ppo.objective_terms(model,samples,prepared);terms['loss'].backward()
    assert bool(torch.isfinite(terms['loss'])) and model.actor[0].weight.grad[:,77].abs().sum()>0
    # No Adam.step() is called. Codec's empty optimizer state remains step zero.
    model.zero_grad();opt=torch.optim.Adam(model.parameters(),lr=3e-4)
    protocol=dict(action_schema=encoder.SCHEMA,economy_epoch=encoder.EPOCH,contract_sha256=model_io.CONTRACT_SHA256)
    bundle=model_io.make_bundle(model,opt,training_updates=0,complete=True,protocol=protocol,parent_sha='0'*64,
        lineage=dict(cpu_synthetic_test=True),collection_states={},purpose='cpu_codec_test',progress={})
    path=a.out/'CPU_TEST_NOT_TRAINED.pt';model_io.atomic_save(bundle,path,allow_test=True)
    model_io.load_model(path,allow_test=True)
    try:model_io.load_model(path)
    except ValueError:rejects.append('cpu_checkpoint_cannot_be_training_parent')
    else:raise AssertionError('CPU test accepted')
    bad=copy.deepcopy(bundle);bad['schema']='strategy-candidates-v4'
    try:model_io.validate(bad,allow_test=True)
    except ValueError:rejects.append('old_checkpoint_schema')
    else:raise AssertionError('Old schema accepted')
    bad=copy.deepcopy(bundle);bad['complete_update_boundary']=False
    try:model_io.validate(bad,resume=True,allow_test=True)
    except ValueError:rejects.append('partial_boundary')
    else:raise AssertionError('Partial resume accepted')
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    try:model_io.atomic_save(bundle,path,allow_test=True,fail_before_replace=True)
    except RuntimeError:rejects.append('atomic_fault_old_file_preserved')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before
    oldtree=ast.parse((HERE.parent/'strategic-typed-training-v1/episode_balanced_ppo.py').read_text());newtree=ast.parse((HERE/'episode_balanced_ppo.py').read_text(encoding='utf-8-sig'))
    funcs=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body if isinstance(n,ast.FunctionDef)}
    assert funcs(oldtree)==funcs(newtree),'PPO objective/update functions changed'
    report=dict(passed=True,cpu_synthetic_only=True,native_games=0,cuda_steps=0,optimizer_steps=0,
        rejection_checks=rejects,ppo_function_AST_exact_to_frozen_parent=True,
        synthetic_build_gradient_l1=float(model.actor[0].weight.grad[:,77].abs().sum()) if model.actor[0].weight.grad is not None else 'checked before zero_grad',
        checkpoint_purpose='cpu_codec_test, rejected as actual training parent',
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')})
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
