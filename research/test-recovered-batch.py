import importlib.util
import json
from pathlib import Path
import numpy as np
import torch

r=Path('/mnt/g/Heroes3-AI-Lab/research')
spec=importlib.util.spec_from_file_location('recovered_graph',r/'recovered-graph.py')
graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)
folder=Path('/root/heroes3-ai-lab/datasets/teacher-balanced-v1/validation')
path=next(p for p in sorted(folder.glob('*.json')) if 'decisions' in json.loads(p.read_text()))
metadata=json.loads(path.read_text());observations=[]
with np.load(path.with_suffix('.npz'),allow_pickle=False) as archive:
    for t in range(min(3,len(metadata['decisions']))):
        nodes={};edges={}
        for key in archive.files:
            if not key.startswith(f'{t}/'):continue
            parts=key.split('/')
            if parts[1]=='nodes':nodes[parts[2]]=archive[key]
            elif parts[1]=='edges':edges.setdefault(tuple(parts[2].split('|')),{})[parts[3]]=archive[key]
        observations.append(dict(nodes=nodes,edges=edges,active_action_ids=archive[f'{t}/legal_ids']))
pair=graph.RecoveredPair().eval()
torch.set_num_threads(1)
checks=[]
with torch.inference_mode():
    for side,role in enumerate(['attacker','defender']):
        model=pair.models[role]
        samples=model.encode_batch(observations)
        logits,values=pair(*graph.head_collate(samples))
        for i,obs in enumerate(observations):
            alone,value=model(obs)
            torch.testing.assert_close(logits[i,:len(alone)],alone,atol=2e-4,rtol=3e-4)
            torch.testing.assert_close(values[i],value,atol=2e-4,rtol=3e-4)
        checks.append(role+': batched graph equals independent graph, including active action offsets')
before={k:v.clone() for k,v in pair.state_dict().items()}
sample=pair.models['attacker'].encode_batch(observations[:1])
optimizer=torch.optim.Adam([p for p in pair.parameters() if p.requires_grad],lr=1e-4)
logits,values=pair(*graph.head_collate(sample))
loss=-logits.log_softmax(-1)[0,0]+values.square().mean()
loss.backward();optimizer.step()
changed=[]
for name,value in pair.state_dict().items():
    if not torch.equal(value,before[name]):changed.append(name)
assert changed and all('policy_head' in k or 'value_head' in k for k in changed)
checks.append('Backpropagation updates heads and preserves every frozen graph parameter')
pair.save('/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt',adapted=False)
# Save untouched weights for actual training; gradient probe is not a trained contender.
initial=graph.RecoveredPair();initial.save('/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt',adapted=False)
(r/'recovered-batch-contract.json').write_text(json.dumps(dict(passed=True,checks=checks,
    initial_pair='/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt',gradient_probe_excluded=True),indent=2))
print(checks,flush=True)
