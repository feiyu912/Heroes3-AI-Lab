"""Bound rollout/minibatch floating-point error on cached real public features."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import torch
import sys

r=Path('/mnt/g/Heroes3-AI-Lab/research')
spec=importlib.util.spec_from_file_location('recovered',r/'recovered-graph.py')
graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)
torch.set_num_threads(2)
initial=sys.argv[1] if len(sys.argv)>1 else '/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt'
pair=graph.RecoveredPair(initial).cuda().eval()
folder=Path('/root/heroes3-ai-lab/datasets/teacher-balanced-v1/train')
samples=[]
for path in sorted(folder.glob('*.json'))[:8]:
    metadata=json.loads(path.read_text())
    if 'decisions' not in metadata:continue
    with np.load(path.with_suffix('.npz'),allow_pickle=False) as archive:
        for t in range(min(8,len(metadata['decisions']))):
            nodes={};edges={}
            for key in archive.files:
                if not key.startswith(f'{t}/'):continue
                parts=key.split('/')
                if parts[1]=='nodes':nodes[parts[2]]=archive[key]
                elif parts[1]=='edges':edges.setdefault(tuple(parts[2].split('|')),{})[parts[3]]=archive[key]
            for side,role in enumerate(['attacker','defender']):
                obs=dict(nodes=nodes,edges=edges,active_action_ids=archive[f'{t}/legal_ids'],lab_side=side)
                with torch.inference_mode():samples+=pair.models[role].encode_batch([obs])
assert len(samples)>64
results=[]
with torch.inference_mode():
    reference=[]
    for start in range(0,len(samples),24):
        batch=graph.head_collate(samples[start:start+24],'cuda');logits,_=pair(*batch)
        reference.extend([row[:len(s[0])].log_softmax(-1) for row,s in zip(logits,samples[start:start+24])])
    for size in [1,4,8,32,64]:
        maximum=0.
        for start in range(0,len(samples),size):
            subset=samples[start:start+size];logits,_=pair(*graph.head_collate(subset,'cuda'))
            for j,s in enumerate(subset):
                actual=logits[j,:len(s[0])].log_softmax(-1)
                maximum=max(maximum,float((actual-reference[start+j]).abs().max()))
        assert maximum<=2e-4,(size,maximum)
        results.append(dict(batch_size=size,maximum_log_probability_error=maximum))
out=dict(passed=True,checkpoint=initial,real_observations=len(samples),rollout_batch_size=24,results=results,
    tolerance_absolute=2e-4,tolerance_relative=0.,maximum_relative_ratio_error_bound=float(np.expm1(2e-4)),
    justification='Float32 head logits have large common offsets; different GEMM batch shapes introduce rounding. Bound is 0.0201% in PPO ratio, far below 20% clipping. No optimizer update performed.')
(r/'cuda-recompute-contract.json').write_text(json.dumps(out,indent=2));print(out,flush=True)
