"""True calibrated initialization and CPU-only codec recovery, no optimizer step."""
import argparse,ast,copy,hashlib,json,random
from pathlib import Path
import torch
import encoder,model_io
HERE=Path(__file__).resolve().parent
INITIAL=HERE.parent/'strategic-learned-build-exploration-v1/calibration-01/build-offset-initialization.pt'
SHA='40eccc511fbc61b84b86e75b5aec102781835f2574db809f9a698f9a81db6d97'
def equal(a,b):
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and torch.equal(a.cpu(),b.cpu())
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1);model,initial,digest=model_io.load_model(INITIAL,'cpu');assert digest==SHA
    assert float(model.actor.build_bias.detach())==1.5
    opt=torch.optim.Adam(model.parameters(),lr=3e-4)
    protocol=dict(schema='strategic-learned-build-exploration-training-v1',architecture_version=model_io.architecture.ARCHITECTURE_VERSION,
        action_schema=encoder.SCHEMA,economy_epoch=encoder.EPOCH,contract_sha256=model_io.CONTRACT_SHA256)
    bundle=model_io.make_bundle(model,opt,training_updates=0,complete=True,protocol=protocol,parent_sha=digest,
        lineage=dict(CPU_codec_only=True),collection_states={},purpose='cpu_codec_test',progress={})
    assert 'actor.build_bias' in bundle['parameter_groups'][0] and bundle['optimizer_steps_total']==0
    path=a.out/'CPU_TEST_NOT_TRAINED.pt';model_io.atomic_save(bundle,path,allow_test=True)
    restored,rb,rd=model_io.load_model(path,'cpu',allow_test=True);opt2=torch.optim.Adam(restored.parameters(),lr=3e-4)
    model_io.restore_training(rb,restored,opt2,protocol_sha=bundle['protocol_sha256'],allow_test=True)
    assert model_io.tensor_sha(restored.state_dict())==model_io.tensor_sha(model.state_dict()) and equal(opt.state_dict(),opt2.state_dict())
    expected=torch.rand(9);py=[random.random() for _ in range(3)];torch.manual_seed(711);random.seed(711)
    model_io.restore_training(rb,restored,opt2,protocol_sha=bundle['protocol_sha256'],allow_test=True)
    assert torch.equal(expected,torch.rand(9)) and py==[random.random() for _ in range(3)]
    qpath=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-build-training-01/cell-00/admitted/samples.jsonl')
    sample=next(json.loads(s) for s in qpath.read_text().splitlines() if json.loads(s)['action_type']=='build');q=sample['request']
    logits,value=model(**encoder.collate([q]));bias=model.actor.build_bias
    build=sample['action'];move=next(i for i,c in enumerate(q['candidates']) if c['op']=='move')
    assert float(torch.autograd.grad(logits[0,build],bias,retain_graph=True)[0])==1
    assert float(torch.autograd.grad(logits[0,move],bias,retain_graph=True)[0])==0
    assert torch.autograd.grad(value[0],bias,allow_unused=True)[0] is None
    rejects=[]
    for case in ('old_format','wrong_architecture','partial','protocol_changed','CPU_as_CUDA','missing_bias_parameter','missing_optimizer_bias_binding'):
        bad=copy.deepcopy(bundle);protocol_sha=bundle['protocol_sha256'];device='cpu'
        if case=='old_format':bad['format']='strategic-learned-build-ppo-checkpoint-v1'
        if case=='wrong_architecture':bad['architecture_version']='old'
        if case=='partial':bad['complete_update_boundary']=False
        if case=='protocol_changed':protocol_sha='0'*64
        if case=='CPU_as_CUDA':device='cuda'
        if case=='missing_bias_parameter':bad['state_dict'].pop('actor.build_bias')
        if case=='missing_optimizer_bias_binding':bad['parameter_groups'][0].remove('actor.build_bias')
        before=model_io.tensor_sha(restored.state_dict());ob=model_io.cpu_tree(opt2.state_dict());rng=torch.get_rng_state().clone();python=random.getstate()
        try:model_io.restore_training(bad,restored,opt2,protocol_sha=protocol_sha,device=device,allow_test=True)
        except (ValueError,AssertionError,RuntimeError):rejects.append(case)
        else:raise AssertionError('Invalid accepted '+case)
        assert before==model_io.tensor_sha(restored.state_dict()) and equal(ob,opt2.state_dict()) and torch.equal(rng,torch.get_rng_state()) and python==random.getstate()
    try:model_io.load_model(path)
    except ValueError:rejects.append('cpu_test_is_not_training_parent')
    else:raise AssertionError('CPU test parent accepted')
    funcs=lambda p:{n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef)}
    assert funcs(HERE/'episode_balanced_ppo.py')==funcs(HERE.parent/'strategic-learned-economy-policy-v1/episode_balanced_ppo.py')
    report=dict(passed=True,CPU_only=True,native_games=0,cuda_steps=0,optimizer_steps=0,initialization_sha256=digest,
        build_bias=1.5,architecture_version=model_io.architecture.ARCHITECTURE_VERSION,Adam_binding_includes_build_bias=True,
        model_Adam_empty_state_CPU_Python_RNG_exact=True,build_bias_derivative_build1_move0_criticNone=True,
        rejection_checks=rejects,invalid_resume_preserves_model_optimizer_CPU_Python_RNG=True,PPO_function_AST_unchanged=True,
        source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')},
        limitation='Empty Adam CPU codec,0optimizer steps; real post-update CUDA Adam/new-bias-moment recovery must be audited after training.')
    (a.out/'AUDIT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
