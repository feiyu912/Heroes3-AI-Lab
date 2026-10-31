"""Evidence helpers; no entry point starts games or CUDA."""
import hashlib,json,random,shutil
from pathlib import Path
B64='1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936'
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_args(a):
    assert sha(a.checkpoint)==B64 and not a.resume
    assert (a.workers,a.updates,a.rollout,a.mode)==(8,4,32,'last')
    assert a.opponents==['BattleAI','MMAI_MODEL'] and a.native_opponent_device=='cpu'
    assert a.learning_rate==1e-6 and a.head_learning_rate==1e-5 and a.epochs==2
    assert a.gamma==1 and a.step_cost==0 and a.shaping==.5 and a.entropy_coef==.005
    assert a.seed==2026102008 and a.rotate_every==16 and a.first_battle
    assert a.no_auto_microbatch and a.microbatch==8
def verify_freeze(path):
    d=json.loads(Path(path).read_text());assert d['schema']=='battle-resume-bounded-last-v1'
    assert all(sha(p)==h for p,h in d['input_sha256'].items()),'Frozen input changed'
    return d
def capture_local(folder,frozen):
    out=Path(folder)/'source/resume-20261020';out.mkdir()
    for p in HERE.glob('*.py'):shutil.copyfile(p,out/p.name)
    (out/'FREEZE.json').write_text(json.dumps(frozen,indent=2))
def snapshot(model):return {n:p.detach().cpu().clone() for n,p in model.named_parameters()}
def delta(model,before):
    import torch
    changed=[];sq=0.;frozen=0
    for n,p in model.named_parameters():
        d=p.detach().cpu().double()-before[n].double()
        if d.ne(0).any():
            assert p.requires_grad,'Frozen graph parameter changed '+n
            changed.append(n);sq+=float(d.square().sum())
        if not p.requires_grad:frozen+=1
    assert changed,'No parameter change'
    return dict(changed_tensors=len(changed),l2=sq**.5,unchanged_frozen_tensors=frozen,changed_parameter_names=changed)
def install_step_counter(optimizer):
    counter={'steps':0}
    def increment(*unused):counter['steps']+=1
    optimizer.register_step_post_hook(increment);return counter
def numpy_rng():
    import numpy as np
    n=np.random.get_state();return dict(engine=n[0],keys=n[1].tolist(),position=n[2],has_gauss=n[3],cached=n[4])
def save_rollout(folder,iteration,payload):
    import torch,os
    p=Path(folder)/('rollout-%d.pt'%iteration);tmp=p.with_suffix('.tmp')
    torch.save(payload,tmp);os.replace(tmp,p)
def equal(a,b):
    import torch
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and torch.equal(a.cpu(),b.cpu())
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b
def check_readback(path,model,optimizer,graph,steps):
    import torch
    cpu_rng=torch.get_rng_state().clone();python_rng=random.getstate()
    try:
        b=torch.load(path,map_location='cpu',weights_only=True);other=graph.FullGraphPair(path,'last').cpu().eval()
        assert equal(model.state_dict(),other.state_dict()) and equal(optimizer.state_dict(),b['optimizer_state_dict'])
        assert b['actual_Adam_steps']==steps and b['complete_update_boundary'] and not b['native_environment_restorable']
        assert all(0<int(s['step'])<=steps for s in b['optimizer_state_dict']['state'].values())
        assert equal(cpu_rng,b['torch_rng_state']) and equal(torch.cuda.get_rng_state_all(),b['cuda_rng_states'])
        assert b['python_rng_state']==python_rng and b['numpy_rng_state']==numpy_rng()
        assert all(sha(p)==h for p,h in b['frozen_inputs']['input_sha256'].items())
        return dict(model_exact=True,Adam_exact=True,global_RNG_payload_exact=True,actual_Adam_steps=steps,native_environment_restored=False)
    finally:torch.set_rng_state(cpu_rng);random.setstate(python_rng)

