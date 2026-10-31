"""Verify learned independent aliases, using only training observations."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import torch

r=Path('/mnt/g/Heroes3-AI-Lab/research')
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,r/file)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
graph=module('recovered','recovered-graph.py')
exporter=module('finetuned_export','export-recovered-onnx.py')
upstream=module('upstream','upstream-policy.py')
torch.set_num_threads(1);torch.manual_seed(2026101503)
pair=graph.RecoveredPair('/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt').eval()
with torch.no_grad():
    for parameter in pair.parameters():parameter.add_(torch.randn_like(parameter)*1e-5)
root=Path('/root/heroes3-ai-lab/models/contract-tests/export')
checkpoint=root/'perturbed-pair.pt';pair.save(str(checkpoint),test_only=True)
exporter.export(checkpoint,root/'onnx')
observations=[]
folder=Path('/root/heroes3-ai-lab/datasets/teacher-balanced-v1/train')
for path in sorted(folder.glob('*.json'))[:4]:
    metadata=json.loads(path.read_text())
    with np.load(path.with_suffix('.npz'),allow_pickle=False) as archive:
        for t in sorted(set([0,len(metadata['decisions'])//2,len(metadata['decisions'])-1])):
            nodes={};edges={}
            for key in archive.files:
                if not key.startswith(f'{t}/'):continue
                parts=key.split('/')
                if parts[1]=='nodes':nodes[parts[2]]=archive[key]
                elif parts[1]=='edges':edges.setdefault(tuple(parts[2].split('|')),{})[parts[3]]=archive[key]
            observations.append(dict(nodes=nodes,edges=edges,active_action_ids=archive[f'{t}/legal_ids']))
results=[]
for role in ['attacker','defender']:
    policy=upstream.UpstreamPolicy(root/'onnx'/f'{role}.onnx')
    maximum=0.;ties=0
    for observation in observations:
        action,probabilities,value=policy.predict(observation)
        with torch.inference_mode():logits,expected_value=pair.models[role](observation)
        expected=logits.softmax(-1).numpy()
        np.testing.assert_allclose(probabilities,expected,atol=4e-5,rtol=3e-4)
        np.testing.assert_allclose(value,float(expected_value),atol=5e-4,rtol=3e-4)
        maximum=max(maximum,float(np.max(np.abs(expected-probabilities))))
        if action!=int(observation['active_action_ids'][int(logits.argmax())]):
            assert float(expected.max()-expected[np.argmax(probabilities)])<=1e-4,'Non-tie greedy mismatch'
            ties+=1
    results.append(dict(role=role,observations=len(observations),maximum_probability_error=maximum,near_tie_greedy_differences=ties))
result=dict(passed=True,results=results,all_parameter_arrays_independently_perturbed=True,
    perturbation_not_a_training_candidate=True,training_observations_only=True,
    note='Synthetic weights verify mapping of every learnable alias; selected real model still needs its own numerical/live verification')
(r/'finetuned-export-contract.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
