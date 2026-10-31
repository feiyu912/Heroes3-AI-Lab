"""Audit real serialized CPU model/Adam/RNG boundaries from synthetic games."""
import json
from pathlib import Path
import subprocess
import sys

from parallel_trainer import torch, read_bundle, schedule, restore

root=Path(sys.argv[1]);out=root/'TRAINER_CPU_AUDIT_02.json'
if out.exists():
    raise ValueError('Refuse overwrite')
full,full_sha=read_bundle(root/'trainer-cpu-continuous-02/update-2.pt')
resumed,resumed_sha=read_bundle(root/'trainer-cpu-resume-02/update-2.pt')
split,_=read_bundle(root/'trainer-cpu-split-02/update-1.pt')
first,_=read_bundle(root/'trainer-cpu-continuous-02/update-1.pt')
partial,_=read_bundle(root/'trainer-cpu-partial-02/failed-partial-not-resumable.pt')


def compare(a,b):
    if isinstance(a,torch.Tensor):
        return dict(equal=torch.equal(a,b),max_abs=float((a.double()-b.double()).abs().max()) if a.numel() else 0.)
    if isinstance(a,dict):
        if a.keys()!=b.keys(): return dict(equal=False,max_abs=None)
        items=[compare(a[k],b[k]) for k in a]
    elif isinstance(a,(list,tuple)):
        if len(a)!=len(b): return dict(equal=False,max_abs=None)
        items=[compare(x,y) for x,y in zip(a,b)]
    else:
        return dict(equal=a==b,max_abs=0. if a==b else None)
    return dict(equal=all(i['equal'] for i in items),max_abs=max((i['max_abs'] for i in items if i['max_abs'] is not None),default=0.))


comparisons={name:compare(full[name],resumed[name]) for name in ('state_dict','optimizer','torch_rng','cuda_rng','python_rng','collection_episode_generator_states')}
initial=compare(first['state_dict'],split['state_dict'])
optimizer=torch.optim.Adam([torch.nn.Parameter(torch.zeros(1))])
rejected=False
try:
    restore(partial,optimizer,torch.device('cpu'),partial['protocol_sha256'],2)
except ValueError as error:
    rejected='partial' in str(error).lower() or 'complete-update' in str(error).lower()
balanced={}
for count in (2,4,8,24):
    jobs=schedule(1,count,2026102300)
    matrix={}
    for job in jobs:
        role='red' if job['red']=='DirectorAI' else 'blue'
        opponent=job['blue'] if role=='red' else job['red']
        key=f"{job['map']}:{role}:{opponent}"
        matrix[key]=matrix.get(key,0)+1
    balanced[str(count)]=dict(episodes=len(jobs),cells=len(matrix),counts=list(matrix.values()),valid=len(matrix)==8 and len(set(matrix.values()))==1)
report=dict(cpu_synthetic_games=True,real_serialized_torch_checkpoints=True,CUDA_training_tested=False,
    full_sha256=full_sha,resumed_sha256=resumed_sha,protocol_equal=full['protocol_sha256']==resumed['protocol_sha256'],
    first_update_model_comparison=initial,final_boundary_comparisons=comparisons,
    full_optimizer_steps=full['optimizer_steps_total'],resume_optimizer_steps=resumed['optimizer_steps_total'],
    partial_real_optimizer_steps=partial['optimizer_steps_total'],partial_complete=partial['complete_update_boundary'],
    partial_resume_rejected=rejected,initial_trained_preserved=bool(first['lineage']['parent_trained']),
    schedule=balanced,
    note='Bitwise equality is reported rather than assumed. Dynamic microbatch sizes can produce floating differences; CUDA recovery still requires its own native/device audit.')
report['passed']=report['protocol_equal'] and initial['equal'] and all(v['equal'] for v in comparisons.values()) and full['optimizer_steps_total']==resumed['optimizer_steps_total']==8 and partial['optimizer_steps_total']==1 and not partial['complete_update_boundary'] and rejected and all(v['valid'] for v in balanced.values())
out.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
