"""Real observation links, padding and action-order invariance for the new scorer."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import torch
from decision_model import load_model, linked_features, collate

r=Path(__file__).parent
spec=importlib.util.spec_from_file_location('lab',r/'lab-env.py')
lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)
scenarios=json.loads((r/'scenarios-v2.json').read_text())
samples=[]
for i in [0,6]:
    # New process would be needed for different engine configs; same env reset suffices here.
    if i==0: env=lab.make_env(scenarios[0]['map'],20261015,'attacker')
    obs,_=env.reset()
    sample=linked_features(obs);samples.append(sample)
    e,c,a,ids=sample
    links=c[:,186:].astype(int)
    assert (links[:,0]>=0).all()
    assert (links[links>=0]<len(e)).all()
    for j,action in enumerate(ids):
        by=obs['edges'][('Action','By','Unit')]['index']
        actor=int(by[1,np.flatnonzero(by[0]==action)[0]])
        np.testing.assert_array_equal(e[links[j,0],:35],obs['nodes']['Unit'][actor])
    if i==0:
        obs,_,_,_,_=env.step(int(ids[-1]))
        samples.append(linked_features(obs))
model,_=load_model('/root/heroes3-ai-lab/models/linked-v4/initial.pt')
torch.set_num_threads(1)
with torch.inference_mode():
    for sample in samples:
        x,v=model(*collate([sample]))
        y,w=model(*collate([sample,*samples]))
        torch.testing.assert_close(x[0],y[0,:x.shape[1]],atol=2e-6,rtol=2e-5)
        torch.testing.assert_close(v[0],w[0],atol=2e-6,rtol=2e-5)
        e,c,a,ids=sample
        p=np.arange(len(ids))[::-1].copy()
        z,_=model(*collate([(e,c[p],a,ids[p])]))
        torch.testing.assert_close(x[0,p],z[0])
result=dict(passed=True,samples=len(samples),checks=['Actor link maps to actual unit attributes','Links stay within entity set',
    'Padding does not alter logits/value','Candidate permutation permutes logits'],multi_target_limitation='Primary target and first landing embeddings; aggregate attributes cover additional targets')
(r/'linked-contract-tests.json').write_text(json.dumps(result,indent=2));print(result)
env.close()
