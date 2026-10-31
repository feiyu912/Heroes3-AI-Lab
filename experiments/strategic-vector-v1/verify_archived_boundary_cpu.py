"""Isolate serialization/Adam/RNG exactness using identical archived batches, not new games."""
import json
from pathlib import Path
import random
import sys

from parallel_trainer import (torch,read_bundle,restore,model_from_bundle,ppo_update,
                              save_checkpoint,optimizer_steps)

root=Path(sys.argv[1]);out=root/'archived-boundary-cpu-01';out.mkdir(exist_ok=False)
torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
zero,_=read_bundle(root/'trainer-cpu-split-02/update-0.pt')
one,one_sha=read_bundle(root/'trainer-cpu-split-02/update-1.pt')


def rows_from(directory,update):
    rows=[];episodes=[]
    for path in sorted(directory.glob(f'update-{update:03d}-wave-*')):
        rows.extend(json.loads(line) for line in (path/'accepted-rollout.jsonl').open())
        episodes.extend(json.loads((path/'batch.json').read_text())['episodes'])
    return rows,episodes


def equal(a,b):
    if isinstance(a,torch.Tensor): return isinstance(b,torch.Tensor) and torch.equal(a,b)
    if isinstance(a,dict): return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(tuple,list)): return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b


model=model_from_bundle(zero,'cpu');optimizer=torch.optim.Adam(model.parameters(),lr=.0003)
torch.set_rng_state(zero['torch_rng']);random.setstate(zero['python_rng'])
rows,episodes=rows_from(root/'trainer-cpu-split-02',1)
ppo_update(model,optimizer,rows,'cpu',episodes=episodes,epochs=2,minibatch_size=16)
update1_match=equal(model.state_dict(),one['state_dict']) and equal(optimizer.state_dict(),one['optimizer']) and torch.equal(torch.get_rng_state(),one['torch_rng'])
boundary_rng=torch.get_rng_state().clone();boundary_python=random.getstate()
save_checkpoint(model,optimizer,out/'actual-roundtrip.pt',update=1,complete=True,
    protocol=one['protocol'],protocol_sha=one['protocol_sha256'],parent_sha=one_sha,
    lineage=one['lineage'],collection_states=one['collection_episode_generator_states'],attempted_update=1,progress=None)
serialized,_=read_bundle(out/'actual-roundtrip.pt')
rows,episodes=rows_from(root/'trainer-cpu-resume-02',2)
torch.set_rng_state(boundary_rng);random.setstate(boundary_python)
ppo_update(model,optimizer,rows,'cpu',episodes=episodes,epochs=2,minibatch_size=16)
continuous=dict(state=model.state_dict(),optimizer=optimizer.state_dict(),torch_rng=torch.get_rng_state().clone(),python_rng=random.getstate())
loaded=model_from_bundle(serialized,'cpu');loaded_optimizer=torch.optim.Adam(loaded.parameters(),lr=.0003)
restore(serialized,loaded_optimizer,torch.device('cpu'),serialized['protocol_sha256'],2)
ppo_update(loaded,loaded_optimizer,rows,'cpu',episodes=episodes,epochs=2,minibatch_size=16)
comparisons=dict(model=equal(continuous['state'],loaded.state_dict()),Adam=equal(continuous['optimizer'],loaded_optimizer.state_dict()),
    CPU_RNG=torch.equal(continuous['torch_rng'],torch.get_rng_state()),Python_RNG=continuous['python_rng']==random.getstate(),
    collection_episode_RNG=equal(serialized['collection_episode_generator_states'],one['collection_episode_generator_states']))
report=dict(test_scope='Identical archived full-terminal batches; isolates serialization/optimizer/RNG, not asynchronous native regeneration',
    CPU_only=True,CUDA_rng_restored=False,real_file_saved_loaded=True,update1_reproduces_actual_checkpoint_exactly=update1_match,
    after_next_update_bitwise_comparisons=comparisons,optimizer_steps=optimizer_steps(loaded_optimizer),
    original_async_audit_remains_failed='TRAINER_CPU_AUDIT_02.json',
    passed=update1_match and all(comparisons.values()) and optimizer_steps(loaded_optimizer)==8)
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
