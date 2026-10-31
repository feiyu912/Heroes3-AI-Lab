"""An interrupted checkpoint write must preserve the last usable model."""
import hashlib
import importlib.util
import json
from pathlib import Path
import torch

r=Path('/mnt/g/Heroes3-AI-Lab/research')
spec=importlib.util.spec_from_file_location('recovered',r/'recovered-graph.py')
graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)
initial='/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt'
pair=graph.RecoveredPair(initial)
destination=Path('/root/heroes3-ai-lab/models/contract-tests/atomic-pair.pt')
pair.save(str(destination),test_only=True)
before=hashlib.sha256(destination.read_bytes()).hexdigest()
restored=graph.RecoveredPair(str(destination))
assert all(torch.equal(v,restored.state_dict()[name]) for name,v in pair.state_dict().items())
save=torch.save
def interrupted(data,path):
    Path(path).write_bytes(b'incomplete checkpoint')
    raise RuntimeError('Deliberately interrupted write')
try:
    torch.save=interrupted
    try:pair.save(str(destination),test_only=True)
    except RuntimeError as error:assert str(error)=='Deliberately interrupted write'
    else:raise AssertionError('Interrupted save was not detected')
finally:torch.save=save
assert hashlib.sha256(destination.read_bytes()).hexdigest()==before
assert not list(destination.parent.glob(destination.name+'.tmp-*'))
result=dict(passed=True,roundtrip_weights_equal=True,interrupted_write_preserves_last_checkpoint=True,
    temporary_files_cleaned=True,probe_not_a_training_candidate=True)
(r/'atomic-checkpoint-contract.json').write_text(json.dumps(result,indent=2));print(result)
