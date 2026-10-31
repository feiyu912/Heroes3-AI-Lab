"""One saved CPU bundle read; no model, forward, optimizer, or CUDA work."""
from pathlib import Path
import os,json,hashlib,fcntl,sys
OUT=Path(__file__).resolve().parent;PROJECT=OUT.parents[2]
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
resource=Path('/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/WSL迁出-20261025/files/root/heroes3-ai-lab/evaluations')
checkpoint=PROJECT/'experiments/ubuntu-native-takeover-20261025/verified-repair/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01/candidate-micro/update-61.pt'
handles=[]
try:
 for name in ['.gpu-learner-lock','.pool-lock']:
  f=(resource/name).open('r');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);handles.append(f)
 import torch
 torch.set_num_threads(1);assert not torch.cuda.is_initialized()
 raw=checkpoint.read_bytes();assert hashlib.sha256(raw).hexdigest()=='4725dab0332ad93f3806084ce1fc01803e77f5e5ee6ca861d452b63892062840'
 b=torch.load(checkpoint,map_location='cpu',weights_only=True);assert b['actual_Adam_steps']==7808 and b['completed_updates']==61
 adam=b['optimizer_state_dict'];rows=[];groups=[]
 for gi,g in enumerate(adam['param_groups']):
  metadata={k:v for k,v in g.items() if k!='params'};groups.append(dict(group=gi,tensors=len(g['params']),metadata=metadata))
  for pid in g['params']:
   s=adam['state'][pid];m=s['exp_avg'];v=s['exp_avg_sq'];assert m.device.type==v.device.type=='cpu' and torch.isfinite(m).all() and torch.isfinite(v).all() and (v>=0).all()
   rows.append(dict(group=gi,parameter_id=pid,shape=list(m.shape),elements=m.numel(),per_parameter_step=int(s['step']),first_moment_nonzero=int(torch.count_nonzero(m)),second_moment_nonzero=int(torch.count_nonzero(v)),first_moment_L2=float(torch.linalg.vector_norm(m.double())),second_moment_sqrt_L2=float(torch.sqrt(v.double().sum())),first_moment_max_abs=float(m.abs().max()),second_moment_max=float(v.max())))
 assert len(rows)==194 and not torch.cuda.is_initialized()
 result=dict(passed=True,checkpoint=str(checkpoint),checkpoint_sha256=hashlib.sha256(raw).hexdigest(),cumulative_Adam_calls=b['actual_Adam_steps'],groups=groups,slots=rows,total_slots=len(rows),nonzero_first_moment_slots=sum(r['first_moment_nonzero']>0 for r in rows),nonzero_second_moment_slots=sum(r['second_moment_nonzero']>0 for r in rows),per_parameter_step_min=min(r['per_parameter_step'] for r in rows),per_parameter_step_max=max(r['per_parameter_step'] for r in rows),new_forward_calls=0,new_optimizer_steps=0,model_constructed=False,optimizer_constructed=False,GPU_initialized=False,canonical_locks=[dict(path=str(resource/n),fd=f.fileno(),inode=os.fstat(f.fileno()).st_ino,device=os.fstat(f.fileno()).st_dev) for n,f in zip(['.gpu-learner-lock','.pool-lock'],handles)])
 (OUT/'ADAM_HISTORY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['slots']},indent=2))
finally:
 for f in reversed(handles):fcntl.flock(f,fcntl.LOCK_UN);f.close()
