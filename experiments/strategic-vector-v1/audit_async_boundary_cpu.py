"""End-to-end CPU fake-game continuous/resumed comparison, with exact fields declared."""
import json
from pathlib import Path
import sys

from parallel_trainer import torch,read_bundle


def compare(a,b):
    if isinstance(a,torch.Tensor):
        return dict(equal=torch.equal(a,b),max_abs=float((a.double()-b.double()).abs().max()) if a.numel() else 0.)
    if isinstance(a,dict):
        if a.keys()!=b.keys(): return dict(equal=False,max_abs=0.)
        entries=[compare(a[k],b[k]) for k in a]
    elif isinstance(a,(list,tuple)):
        if len(a)!=len(b): return dict(equal=False,max_abs=0.)
        entries=[compare(x,y) for x,y in zip(a,b)]
    else:
        return dict(equal=a==b,max_abs=abs(a-b) if isinstance(a,(int,float)) and isinstance(b,(int,float)) else 0.)
    return dict(equal=all(e['equal'] for e in entries),max_abs=max((e['max_abs'] for e in entries),default=0.))


def rows_at(root,update):
    return [json.loads(line) for wave in sorted(root.glob(f'update-{update:03d}-wave-*')) for line in (wave/'accepted-rollout.jsonl').open()]


root=Path(sys.argv[1]);suffix=sys.argv[2]
out=root/f'TRAINER_CPU_AUDIT_{suffix}.json'
if out.exists(): raise ValueError('Refuse overwrite')
full_path=root/f'trainer-cpu-continuous-{suffix}'
split_path=root/f'trainer-cpu-split-{suffix}'
resume_path=root/f'trainer-cpu-resume-{suffix}'
full,_=read_bundle(full_path/'update-2.pt');resume,_=read_bundle(resume_path/'update-2.pt')
first,_=read_bundle(full_path/'update-1.pt');split,_=read_bundle(split_path/'update-1.pt')
fields=('request','action','old_logprob','old_value','return','generator_seed','policy_version')
updates=[]
for update,other in ((1,split_path),(2,resume_path)):
    a=rows_at(full_path,update);b=rows_at(other,update)
    updates.append(dict(update=update,rows=len(a),other_rows=len(b),
        comparisons={field:compare([r[field] for r in a],[r[field] for r in b]) for field in fields}))
parts={field:compare(full[field],resume[field]) for field in ('state_dict','optimizer','torch_rng','cuda_rng','python_rng')}
states=lambda b:{wave:info['episode_generator_states'] for wave,info in b['collection_episode_generator_states'].items()}
parts['episode_generator_states']=compare(states(full),states(resume))
exact=all(c['equal'] for c in parts.values()) and all(c['equal'] for u in updates for c in u['comparisons'].values())
report=dict(scope='Actual asynchronous/barrier CPU fake-engine regeneration; complete balanced batches, real Adam updates and atomic checkpoint resume',
    suffix=suffix,inference_schedule=full['protocol']['inference_schedule'],synthetic=True,CUDA_tested=False,
    protocol_equal=full['protocol_sha256']==resume['protocol_sha256'],
    first_update_model=compare(first['state_dict'],split['state_dict']),updates=updates,final_comparisons=parts,
    full_optimizer_steps=full['optimizer_steps_total'],resume_optimizer_steps=resume['optimizer_steps_total'],
    checkpoint_provenance_byte_sha_not_compared='Parent lineage differs intentionally; tensor/Adam/RNG and complete rollout fields compared',
    all_declared_fields_bitwise_equal=exact,
    passed_exact=exact and full['protocol_sha256']==resume['protocol_sha256'] and full['optimizer_steps_total']==resume['optimizer_steps_total']==8)
out.write_text(json.dumps(report,indent=2))
print(json.dumps(dict(schedule=report['inference_schedule'],passed_exact=report['passed_exact'],
    first_update_model=report['first_update_model'],final=parts),indent=2))
