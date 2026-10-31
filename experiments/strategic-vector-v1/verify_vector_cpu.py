"""Read-only audit of CPU fake collection, RNG schedule independence and fail-closed batch."""
import copy
import hashlib
import json
from pathlib import Path
import sys

from collect_vector import torch, load_checkpoint_bundle, DEFAULT_CHECKPOINT, collate, sample_ready

root=Path(sys.argv[1])
out=root/'CPU_VECTOR_AUDIT.json'
if out.exists():
    raise ValueError('Refuse overwrite')
torch.set_num_threads(1)
model,_,_=load_checkpoint_bundle(DEFAULT_CHECKPOINT,'cpu')
cases=[]
all_rows=[]
for name in ('synthetic-order-a','synthetic-order-b'):
    directory=root/name
    rows=[json.loads(line) for line in (directory/'accepted-rollout.jsonl').open()]
    batches=[json.loads(line) for line in (directory/'inference-batches.jsonl').open()]
    report=json.loads((directory/'batch.json').read_text())
    maxlog=maxvalue=0.
    for row in rows:
        with torch.no_grad():
            logits,values=model(**collate([row['request']],'cpu'))
            logp=float(logits[0].log_softmax(-1)[row['action']])
        maxlog=max(maxlog,abs(logp-row['old_logprob']))
        maxvalue=max(maxvalue,abs(float(values[0])-row['old_value']))
    all_rows.append(rows)
    cases.append(dict(name=name,samples=len(rows),episodes=len(report['episodes']),batch_sizes=[b['batch_size'] for b in batches],
                      max_abs_logprob_replay_error=maxlog,max_abs_value_replay_error=maxvalue,
                      complete=report['learner_update_allowed'],policy_unchanged=report['policy_unchanged'],
                      native_consumption_all=all(e['native_consumption_verified'] for e in report['episodes']),
                      remaining=report['remaining_processes']))
sequences=[]
for rows in all_rows:
    sequences.append({str(i):[(r['action'],r['request_sha256'],r['generator_seed']) for r in rows if r['episode_index']==i] for i in range(4)})
boundaries=[torch.load(root/name/'collection-boundary.pt',map_location='cpu',weights_only=True) for name in ('synthetic-order-a','synthetic-order-b')]
state_equal=all(torch.equal(boundaries[0]['episode_generator_states'][key],boundaries[1]['episode_generator_states'][key]) for key in boundaries[0]['episode_generator_states'])
bad=json.loads((root/'synthetic-invalid-01/batch.json').read_text())
fixture=json.loads((root.parent/'strategic-policy-v2/fixtures/visible-request.json').read_text())
pending=[(i,b'',copy.deepcopy(fixture)) for i in range(4)]
pending[1][2]['candidates']=pending[1][2]['candidates'][:1]
generators={i:torch.Generator(device='cpu').manual_seed(100+i) for i in range(4)}
before=torch.get_rng_state().clone()
sample_ready(model,pending,generators,torch.device('cpu'))
global_unchanged=torch.equal(before,torch.get_rng_state())
report=dict(synthetic_cpu_only=True,cases=cases,per_env_action_request_seed_sequences_equal=sequences[0]==sequences[1],
            final_per_environment_generator_states_equal=state_equal,global_torch_rng_unchanged_by_sampling=global_unchanged,
            invalid_batch_rejected=bad['status']=='invalid_batch' and bad['accepted_samples']==0 and not bad['learner_update_allowed'] and not (root/'synthetic-invalid-01/accepted-rollout.jsonl').exists(),
            actual_optimizer_steps=0,cuda_execution_verified=False,real_native_vector_collection_verified=False)
report['passed']=all(c['complete'] and c['native_consumption_all'] and c['policy_unchanged'] and not c['remaining'] and c['max_abs_logprob_replay_error']<1e-6 and c['max_abs_value_replay_error']<1e-6 for c in cases) and report['per_env_action_request_seed_sequences_equal'] and state_equal and global_unchanged and report['invalid_batch_rejected']
out.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 1)
