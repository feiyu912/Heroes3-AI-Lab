"""One CPU-only optimization fixture tests actual Adam moments, atomic save and recovery."""
import copy,json,random
from pathlib import Path
import torch
from load_admitted import load
from episode_balanced_ppo import ppo_update,optimizer_steps
from model_io import architecture,make_bundle,atomic_save,read,load_model,restore_training,tensor_sha
HERE=Path(__file__).resolve().parent;OUT=HERE/'checkpoint-cpu-01';OUT.mkdir(exist_ok=False)
torch.set_num_threads(1);torch.manual_seed(51201);random.seed(51201)
parent=HERE.parent/'strategic-policy-v3/checkpoints/typed-from-update2-v4.pt'
model,_,parent_sha=architecture.load_checkpoint_bundle(parent,'cpu')
optimizer=torch.optim.Adam(model.parameters(),lr=3e-4)
samples,episodes,_=load(HERE/'admitted-episode-01');progress={}
# Real CPU fixture step, not a delivered learning branch or GPU update.
ppo_update(model,optimizer,samples,'cpu',progress,episodes=episodes,epochs=1,minibatch_size=len(samples))
assert optimizer_steps(optimizer)==1
protocol={'schema':'typed-codec-cpu-test-v1','purpose':'cpu serialization/optimizer/RNG test only'}
bundle=make_bundle(model,optimizer,training_updates=1,complete=True,protocol=protocol,parent_sha=parent_sha,
    lineage={'test_only':True},collection_states={},purpose='cpu_codec_test',progress=progress)
before_rng=torch.get_rng_state().clone();before_python=random.getstate()
path=OUT/'TEST_ONLY.pt';digest=atomic_save(bundle,path,allow_test=True)
assert torch.equal(before_rng,torch.get_rng_state()) and before_python==random.getstate()
expected_torch=torch.rand(9);expected_python=[random.random() for _ in range(5)]
restored,loaded,read_sha=load_model(path,allow_test=True);assert digest==read_sha
new_optimizer=torch.optim.Adam(restored.parameters(),lr=3e-4)
restore_training(loaded,restored,new_optimizer,protocol_sha=bundle['protocol_sha256'],allow_test=True)
assert torch.equal(expected_torch,torch.rand(9)) and expected_python==[random.random() for _ in range(5)]
assert tensor_sha(restored.state_dict())==tensor_sha(model.state_dict())
def same(a,b):
    if isinstance(a,torch.Tensor):return torch.equal(a,b)
    if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
    if isinstance(a,(tuple,list)):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b
assert same(optimizer.state_dict(),new_optimizer.state_dict())
parameter=dict(restored.named_parameters())['actor.stop_bias'];moment=new_optimizer.state[parameter]
assert int(moment['step'])==1 and float(moment['exp_avg'])!=0
original_bytes=path.read_bytes()
try:atomic_save(bundle,path,allow_test=True,fail_before_replace=True)
except RuntimeError:pass
else:raise AssertionError('Atomic fault did not trigger')
assert path.read_bytes()==original_bytes and not list(OUT.glob('*.tmp'))
rejected=[]
for label in ['cpu_fixture_deployment','old_weights_loader','partial_resume','protocol_change','adam_counter','cpu_as_cuda','bad_moment_shape']:
    bad=copy.deepcopy(bundle)
    try:
        if label=='cpu_fixture_deployment':load_model(path)
        elif label=='old_weights_loader':architecture.model_from_bundle(bad)
        elif label=='partial_resume':
            bad['complete_update_boundary']=False;atomic_save(bad,OUT/'TEST_ONLY_PARTIAL.pt',allow_test=True);read(OUT/'TEST_ONLY_PARTIAL.pt',allow_test=True)
        elif label=='protocol_change':restore_training(bad,restored,new_optimizer,protocol_sha='0'*64,allow_test=True)
        elif label=='adam_counter':bad['optimizer_steps_total']=2;atomic_save(bad,OUT/'BAD.pt',allow_test=True)
        elif label=='cpu_as_cuda':restore_training(bad,restored,new_optimizer,protocol_sha=bundle['protocol_sha256'],device='cuda',allow_test=True)
        elif label=='bad_moment_shape':
            names=bad['parameter_groups'][0];index=names.index('actor.stop_bias');identity=bad['optimizer']['param_groups'][0]['params'][index]
            bad['optimizer']['state'][identity]['exp_avg']=torch.zeros(2);atomic_save(bad,OUT/'BAD.pt',allow_test=True)
    except (ValueError,AssertionError):rejected.append(label)
    else:raise AssertionError('Bad checkpoint accepted '+label)
report=dict(passed=True,cpu_fixture_optimizer_steps=1,cuda_optimizer_steps=0,delivered_schema4_training_updates=0,
            model_and_Adam_exact=True,stop_bias_moment_restored=True,cpu_and_python_rng_exact=True,
            save_does_not_advance_rng=True,atomic_fault_preserved_old_file=True,rejected=rejected,
            checkpoint_sha256=digest,purpose='CPU test only; deployment and CUDA resume rejected')
(OUT/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
