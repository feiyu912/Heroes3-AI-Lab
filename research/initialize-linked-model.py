"""Expand the scorer without changing its initial decisions or value predictions."""
import json
from pathlib import Path
import numpy as np
import torch
from decision_model import DecisionModel, load_model, save_model, collate, load_dataset

r = Path('/mnt/g/Heroes3-AI-Lab/research')
source = json.loads((r/'selected-trained-model.json').read_text())['checkpoint']
original, old_checkpoint = load_model(source)
model = DecisionModel('linked-gnn', original.width)
state = original.state_dict()
old_weight = state.pop('policy.0.weight')
model.load_state_dict(state, strict=False)
with torch.no_grad():
    model.policy[0].weight.zero_()
    model.policy[0].weight[:, :old_weight.shape[1]].copy_(old_weight)
model.eval()
samples=load_dataset('/root/heroes3-ai-lab/datasets/teacher-balanced-v1','validation')[:8]
base=[s['features'] for s in samples]
linked=[(e,np.concatenate((c,np.full((len(c),3),-1,np.float32)),1),a,ids) for e,c,a,ids in base]
with torch.inference_mode():
    x,v=original(*collate(base))
    y,w=model(*collate(linked))
    torch.testing.assert_close(x,y,atol=2e-6,rtol=2e-6)
    torch.testing.assert_close(v,w,atol=2e-6,rtol=2e-6)
path='/root/heroes3-ai-lab/models/linked-v4/initial.pt'
save_model(model,path,source_checkpoint=source,source='Validation-selected v3; zero initialized extra graph associations')
(r/'linked-model-initialization.json').write_text(json.dumps(dict(checkpoint=path,source_checkpoint=source,
    initial_predictions_identical=True,parameters=sum(p.numel() for p in model.parameters())),indent=2))
print(path)
