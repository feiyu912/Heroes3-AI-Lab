"""Independent read-only boundary audit, including actual action-* response files."""
import hashlib,json
from pathlib import Path
import torch
from model_io import read
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/heroes3-ai-lab/evaluations/typed-native-cuda-boundary-v5-01')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def equal(a,b):
    if isinstance(a,torch.Tensor):return isinstance(b,torch.Tensor) and a.dtype==b.dtype and a.shape==b.shape and torch.equal(a,b)
    if type(a)!=type(b):return False
    if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    return a==b
plan=json.loads((ROOT/'PLAN.json').read_text());assert all(sha(Path(p))==h for p,h in plan['source_sha256'].items())
comparison=json.loads((ROOT/'COMPARISON.json').read_text());assert comparison['passed']
results=[]
for update,other in [(1,'split-one'),(2,'resumed')]:
    paths=[ROOT/'continuous'/f'update-{update}.pt',ROOT/other/f'update-{update}.pt']
    a,b=[read(p)[0] for p in paths];assert equal(a,b)
    assert a['training_updates']==update and a['optimizer_steps_total']==(32 if update==1 else 52)
    roots=[ROOT/'continuous'/f'update-{update:02d}',ROOT/other/f'update-{update:02d}']
    counts=[]
    for r in roots:
        audit=json.loads((r/'raw-audit/AUDIT.json').read_text());admit=json.loads((r/'admitted/AUDIT.json').read_text())
        assert audit['whole_game_valid'] and audit['native_game_completed'] and audit['transport_drained'] and not audit['contract_errors']
        assert admit['replay_actions_logprobs_values_rng_exact'] and admit['sampling_device']=='cuda' and admit['optimizer_steps']==0
        counts.append(admit['samples_admitted'])
    names=lambda r:{p.name for pattern in ['request-*.json','action-*.json'] for p in (r/'native/agent').glob(pattern)}
    left,right=[names(r) for r in roots];assert left==right and len(left)==2*counts[0] and counts[0]==counts[1]
    assert all(sha(roots[0]/'native/agent'/name)==sha(roots[1]/'native/agent'/name) for name in left)
    results.append(dict(update=update,full_bundle_values_exact=True,request_and_action_response_files_exact=len(left),
        model_adam_cpu_cuda_python_rng_collection_states_progress_exact=True,
        checkpoint_file_sha256=[sha(p) for p in paths],checkpoint_file_bytes_identical=sha(paths[0])==sha(paths[1]),
        samples=counts[0],optimizer_steps_total=a['optimizer_steps_total']))
out=HERE/'native-boundary-v5-audit-01';out.mkdir(exist_ok=False)
report=dict(passed=True,updates=results,native_games=4,distinct_logical_training_episodes=2,
    continuous_branch_cuda_steps=52,repeat_execution_cuda_steps=52,initial_optimizer_reset=True,
    ability_improvement_claim=False,finaltest_touched=False,
    comparison_scope='Complete saved tensor/scalar/metadata values and actual wire bytes; update2 checkpoint container SHA differs and is explicitly retained. This is not whole checkpoint file byte equality.',
    original_comparison_sha256=sha(ROOT/'COMPARISON.json'))
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
