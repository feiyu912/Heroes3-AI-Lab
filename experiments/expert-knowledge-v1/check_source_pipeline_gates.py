"""CPU-only negative gate checks; does not train or create a game process."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import torch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('source_bc_gates',HERE/'train_source_wait.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
records=[json.loads(line) for line in (m.VARIANT/'candidate-bc-train.jsonl').read_text().splitlines() if line]
m.validate_records(records)
rejected=[]
def rejects(name,call):
    try:call()
    except AssertionError:rejected.append(name)
    else:raise AssertionError('Gate accepted corrupted input: '+name)

for name,key,value in [('non_training_label','split','test'),('wrong_actor','actor_side',1-records[0]['actor_side']),('not_wait_label','action_type',3)]:
    altered=copy.deepcopy(records);altered[0][key]=value
    rejects(name,lambda:m.validate_records(altered))
provenance=m.capture_inputs();m.verify_inputs(provenance)
assert m.model_window([dict(action_type=0,round=1,opposing_actions_before=0),dict(action_type=3,round=1,opposing_actions_before=1),dict(action_type=3,round=2,opposing_actions_before=1)])
assert not m.model_window([dict(action_type=3,round=1,opposing_actions_before=0)]*3)
assert not m.model_window([dict(action_type=0,round=1,opposing_actions_before=0),dict(action_type=3,round=1,opposing_actions_before=1),dict(action_type=3,round=2,opposing_actions_before=2)])
original=m.VARIANT
with tempfile.TemporaryDirectory(prefix='source-bc-gates-') as temporary:
    m.VARIANT=Path(temporary)
    for name in ['candidate-bc-train.jsonl','heldout-scenarios.json']:
        (m.VARIANT/name).write_bytes((original/name).read_bytes())
    checkpoint=m.VARIANT/'synthetic-checkpoint-bytes';checkpoint.write_bytes(b'gate test only; never loaded as model')
    training=dict(checkpoint=str(checkpoint),sha256=m.digest(checkpoint),initial_sha256=m.digest(m.INITIAL),dataset_sha256=m.digest(m.VARIANT/'candidate-bc-train.jsonl'))
    frozen=dict(**training,input_provenance=provenance,heldout_definition_sha256=m.digest(m.VARIANT/'heldout-scenarios.json'))
    def save():m.atomic_json(m.VARIANT/'source-bc-freeze.json',frozen)
    save();m.verify_freeze(training)
    checkpoint.write_bytes(b'tampered')
    rejects('checkpoint_changed',lambda:m.verify_freeze(training))
    checkpoint.write_bytes(b'gate test only; never loaded as model')
    heldout=m.VARIANT/'heldout-scenarios.json';saved=heldout.read_bytes();heldout.write_bytes(saved+b' ')
    rejects('heldout_definition_changed',lambda:m.verify_freeze(training))
    heldout.write_bytes(saved)
    cases=json.loads(saved);cases[0]['sha256']='0'*64;heldout.write_text(json.dumps(cases))
    frozen['heldout_definition_sha256']=m.digest(heldout);save()
    rejects('fixture_hash_mismatch',lambda:m.verify_freeze(training))
    code=m.VARIANT/'synthetic.py';code.write_text('original')
    one=dict(input_hashes={str(code):m.digest(code)},snapshot_hashes={})
    m.verify_inputs(one);code.write_text('changed')
    rejects('code_changed_after_capture',lambda:m.verify_inputs(one))
m.VARIANT=original
torch.set_num_threads(2)
graph=m.load_module('cpu_bc_backward_graph',m.LAB/'research/recovered-graph.py')
pair=graph.RecoveredPair(m.INITIAL).cpu().eval()
observations=[m.unpack(row['observation'],row['actor_side']) for row in records]
cache=pair.encode_features(observations)
batch=graph.head_collate(cache,'cpu')
mask=batch[-1]
labels=torch.tensor([row['observation']['active_action_ids'].index(row['action']) for row in records])
for name,parameter in pair.named_parameters():parameter.requires_grad_('policy_head__' in name)
with torch.no_grad():
    original_logits,_=pair(*batch)
    reference_logp=original_logits.log_softmax(-1).masked_fill(~mask,0).detach().clone()
    reference_prob=original_logits.softmax(-1).detach().clone()
optimizer=torch.optim.Adam([p for p in pair.parameters() if p.requires_grad],lr=1e-4)
before_nll=None
for step in range(2):
    logits,_=pair(*batch)
    nll=torch.nn.functional.cross_entropy(logits,labels)
    logp=logits.log_softmax(-1).masked_fill(~mask,0)
    kl=(reference_prob*(reference_logp-logp)).sum(-1).mean()
    loss=nll+0.1*kl
    assert torch.isfinite(loss)
    optimizer.zero_grad(set_to_none=True);loss.backward()
    assert torch.isfinite(torch.nn.utils.clip_grad_norm_(pair.parameters(),0.5))
    optimizer.step()
    if step==0:before_nll=float(nll.detach())
assert float(nll.detach())<before_nll
result=dict(status='passed',device='CPU only; disposable optimizer check, no CUDA calls or game processes',real_demonstrations_checked=len(records),
    negative_gates_rejected=rejected,actual_model_window_truth_table_passed=True,
    runtime_input_hashes_checked=len(provenance['input_hashes']),source_snapshot_files=len(provenance['snapshot_hashes']),
    real_model_cpu_backward_steps=2,real_model_cpu_initial_nll=before_nll,real_model_cpu_second_step_nll=float(nll.detach()),
    note='Two CPU-only BC/KL optimizer steps on a disposable actual-model copy; no checkpoint saved. Synthetic checkpoint bytes only exercise hash gates; formal CUDA BC and native tests remain pending')
m.atomic_json(original/'source-pipeline-gate-check.json',result)
print(json.dumps(result))
