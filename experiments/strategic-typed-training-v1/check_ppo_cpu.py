"""CPU gradients + fail-before-step checks on actual sealed CUDA/native data."""
import copy,hashlib,importlib.util,json
from pathlib import Path
import torch
from load_admitted import load
from episode_balanced_ppo import prepare_batch,objective_terms,ppo_update,optimizer_steps
HERE=Path(__file__).resolve().parent;TYPED=HERE.parent/'strategic-policy-v3'
spec=importlib.util.spec_from_file_location('_typed_cpu_model',TYPED/'model.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
torch.set_num_threads(1)
model,bundle,checkpoint_sha=module.load_checkpoint_bundle(TYPED/'checkpoints/typed-from-update2-v4.pt','cpu')
samples,episodes,admission=load(HERE/'admitted-episode-01')
assert all(s['policy_sha256']==checkpoint_sha for s in samples)
prepared=prepare_batch(samples,episodes=episodes)
terms=objective_terms(model,samples,prepared);terms['loss'].backward()
assert model.actor.stop_bias.grad is not None and torch.isfinite(model.actor.stop_bias.grad) and float(model.actor.stop_bias.grad)!=0
assert all(p.grad is None or bool(torch.isfinite(p.grad).all()) for p in model.parameters())
stop_gradient=float(model.actor.stop_bias.grad)
before={n:p.detach().clone() for n,p in model.named_parameters()}
negative=[]
for name in ['null_reward','unverified_execution','wrong_operation','bad_action_schema','uncertified_episode','wrong_policy_checkpoint']:
    rows=copy.deepcopy(samples);manifest=copy.deepcopy(episodes)
    if name=='null_reward':rows[0]['return']=None
    if name=='unverified_execution':rows[0]['execution_verified']=False
    if name=='wrong_operation':rows[0]['action_type']='unknown'
    if name=='bad_action_schema':rows[0]['request']['schema']='strategy-candidates-v3'
    if name=='uncertified_episode':manifest[0]['native']['completed']=False
    if name=='wrong_policy_checkpoint':rows[0]['policy_sha256']='0'*64
    optimizer=torch.optim.Adam(model.parameters(),lr=3e-4);progress={}
    try:ppo_update(model,optimizer,rows,'cpu',progress,episodes=manifest,epochs=1)
    except (ValueError,KeyError):pass
    else:raise AssertionError('Bad data accepted: '+name)
    assert optimizer_steps(optimizer)==0 and progress['optimizer_steps']==0 and not progress['completed']
    assert all(torch.equal(before[n],p) for n,p in model.named_parameters())
    negative.append(name)
out=HERE/'ppo-cpu-preflight-01';out.mkdir(exist_ok=False)
result=dict(passed=True,samples=len(samples),real_native_cuda_admission=True,stop_bias_gradient=stop_gradient,
            weighting=prepared['metadata'],negative_cases=negative,cpu_optimizer_steps=0,cuda_optimizer_steps=0,
            scope='Backward gradients and rejection gates only. No learned checkpoint or training win-rate claim.')
(out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
