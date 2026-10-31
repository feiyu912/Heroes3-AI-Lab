#!/usr/bin/env python3
"""CPU-only parameter audit; no inference ablation, optimizer, or game."""
import hashlib
import io
import json
from pathlib import Path
import torch

torch.set_num_threads(1)
HERE=Path(__file__).resolve().parent
RUN=HERE.parent.parent/'strategic-vector-v1/native-cuda-boundary-clean-4env-01/continuous-2'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def stats(delta):
    return {'changed_elements':int(torch.count_nonzero(delta)), 'elements':delta.numel(),
            'l2':float(torch.linalg.vector_norm(delta.double())), 'max_abs':float(delta.abs().max())}
states=[];hashes=[]
for n in range(3):
    raw=(RUN/f'update-{n}.pt').read_bytes()
    states.append(torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True))
    hashes.append(sha(raw))
networks={}
for network in ('actor','critic'):
    key=network+'.0.weight'
    assert tuple(states[0]['state_dict'][key].shape)==(64,49)
    groups={}
    for name,start,end in (('new_state',11,26),('new_candidate',41,49)):
        matrices=[s['state_dict'][key][:,start:end] for s in states]
        assert int(torch.count_nonzero(matrices[0]))==0
        groups[name]={'slice_python':[start,end],'initial_exact_zero':True,
            'update1_from0':stats(matrices[1]-matrices[0]),'update2_from1':stats(matrices[2]-matrices[1]),
            'update2_from0':stats(matrices[2]-matrices[0]),
            'per_column_update2_from0':{str(start+j):stats(matrices[2][:,j]-matrices[0][:,j]) for j in range(end-start)}}
    deltas={}
    for current,previous in ((1,0),(2,1)):
        combined=torch.cat([(states[current]['state_dict'][key]-states[previous]['state_dict'][key]).flatten()
            for key in states[current]['state_dict'] if key.startswith(network+'.')])
        deltas[f'update{current}_from{previous}']=stats(combined)
    networks[network]={'feature_columns':groups,'all_parameters':deltas}
training=json.loads((RUN/'training.json').read_text())
report={'scope':'Actual parameter changes on CPU-loaded CUDA-produced checkpoints. No ablation, no causal attribution to a specific feature, no strategic gain or native result inferred.',
    'checkpoint_sha256':dict(enumerate(hashes)),'networks':networks,
    'real_optimizer_steps_this_run':training['optimizer_steps_this_run'],
    'updates':[{'update':u['update'],'optimizer_steps':u['metrics']['optimizer_steps'],
        'free_choices':u['metrics']['weighting']['free_choices'],'forced_transitions':u['metrics']['weighting']['forced_transitions'],
        'forced_only_minibatches':u['metrics']['forced_only_minibatches']} for u in training['updates']],
    'audit_CUDA_initialized':torch.cuda.is_initialized(),'audit_optimizer_steps':0,
    'audit_sha256':sha(Path(__file__).read_bytes())}
assert not report['audit_CUDA_initialized']
(HERE/'FEATURE_COLUMNS.json').write_text(json.dumps(report,indent=2))
print(json.dumps(networks,indent=2))
