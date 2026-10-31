import importlib.util
import json
from pathlib import Path
import time
import numpy as np
import torch

r=Path(__file__).parent
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,r/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
graph=module('recovered_graph','recovered-graph.py')
upstream=module('upstream_policy','upstream-policy.py')
lab=module('lab','lab-env.py')
torch.set_num_threads(1)
results=[]
for role in ['attacker','defender']:
    path=f'/mnt/g/Heroes3-AI-Lab/models/upstream-v15/{role}.onnx'
    weights,metadata=graph.extract(path)
    model=graph.RecoveredGraph(weights,metadata).eval()
    folder=Path('/root/heroes3-ai-lab/models/recovered-v15');folder.mkdir(parents=True,exist_ok=True)
    torch.save(dict(weights=weights,metadata=metadata,source_onnx=path),folder/(role+'.pt'))
    reference=upstream.UpstreamPolicy(path)
    # Only one engine per process: compare both networks on the same observation corpus.
    if role=='attacker':
        cases=json.loads((r/'scenarios-v2.json').read_text())
        env=lab.make_env(cases[20]['map'],20261015,'attacker')
        obs,_=env.reset();observations=[]
        for _ in range(12):
            observations.append(obs)
            action,_,_=reference.predict(obs)
            obs,_,terminated,truncated,_=env.step(action)
            if terminated or truncated:break
    largest=0.0
    with torch.inference_mode():
        for obs in observations:
            a,p,v=reference.predict(obs)
            logits,value=model(obs)
            probs=logits.softmax(0).numpy()
            np.testing.assert_allclose(probs,p,atol=2e-5,rtol=3e-4)
            np.testing.assert_allclose(float(value),v,atol=2e-5,rtol=3e-4)
            assert int(obs['active_action_ids'][logits.argmax()])==a
            largest=max(largest,float(np.max(np.abs(probs-p))))
    results.append(dict(role=role,observations=len(observations),maximum_probability_error=largest,
        parameters=sum(p.numel() for p in model.parameters()),passed=True))
(r/'recovered-graph-contract.json').write_text(json.dumps(dict(passed=True,results=results,
    limitation='Both side networks checked on attacker observation corpus; live role-specific validation required before training'),indent=2))
print(results,flush=True)
env.close()
