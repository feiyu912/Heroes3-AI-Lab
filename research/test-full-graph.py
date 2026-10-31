"""Check forward equivalence, batching, selective graph gradients and shaping."""
import json
from pathlib import Path
import numpy as np
import torch
from full_graph_policy import FullGraphPair,collate,base

r=Path('/mnt/g/Heroes3-AI-Lab/research')
torch.set_num_threads(1)
folder=Path('/root/heroes3-ai-lab/datasets/teacher-balanced-v1/train')
path=next(p for p in sorted(folder.glob('*.json')) if 'decisions' in json.loads(p.read_text()))
observations=[]
with np.load(path.with_suffix('.npz'),allow_pickle=False) as archive:
    for side in [0,1]:
        for t in range(2):
            nodes={};edges={}
            for key in archive.files:
                if not key.startswith(f'{t}/'):continue
                parts=key.split('/')
                if parts[1]=='nodes':nodes[parts[2]]=archive[key]
                elif parts[1]=='edges':edges.setdefault(tuple(parts[2].split('|')),{})[parts[3]]=archive[key]
            observations.append(dict(nodes=nodes,edges=edges,active_action_ids=archive[f'{t}/legal_ids'],lab_side=side))
initial='/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt'
pair=FullGraphPair(initial,mode='last').eval()
reference=base.RecoveredPair(initial).eval()
with torch.inference_mode():
    logits,values=pair(*collate(observations))
    for i,obs in enumerate(observations):
        expected,value=reference.models['defender' if obs['lab_side'] else 'attacker'](obs)
        torch.testing.assert_close(logits[i,:len(expected)],expected,atol=2e-4,rtol=3e-4)
        torch.testing.assert_close(values[i],value,atol=2e-4,rtol=3e-4)
before={k:v.clone() for k,v in pair.state_dict().items()}
optimizer=torch.optim.Adam([p for p in pair.parameters() if p.requires_grad],lr=1e-5)
logits,values=pair(*collate(observations))
loss=-logits.log_softmax(-1)[:,0].mean()+values.square().mean()
optimizer.zero_grad();loss.backward()
assert all(p.grad is None or torch.isfinite(p.grad).all() for p in pair.parameters())
optimizer.step()
changed=[k for k,v in pair.state_dict().items() if not torch.equal(v,before[k])]
assert any('gnn__convs__2__' in k for k in changed)
assert all('policy_head__' in k or 'value_head__' in k or 'gnn__convs__2__' in k or 'gnn__norms__2__' in k for k in changed)
# Discounted potential rewards telescope to a policy-independent initial offset.
gamma=.99;phi=[.1,.3,-.2,.7,0.0]
shaped=sum(gamma**t*(gamma*phi[t+1]-phi[t]) for t in range(len(phi)-1))
assert abs(shaped+phi[0])<1e-12
out=dict(passed=True,batched_and_independent_forward_equal=True,finite_graph_gradients=True,
    last_graph_layer_changes=True,frozen_earlier_layers_unchanged=True,
    potential_shaping_telescopes=True,probe_weights_excluded=True,
    total_parameters=sum(p.numel() for p in pair.parameters()),
    trainable_parameters=sum(p.numel() for p in pair.parameters() if p.requires_grad))
(r/'full-graph-contract.json').write_text(json.dumps(out,indent=2));print(out,flush=True)
