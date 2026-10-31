#!/usr/bin/env python3
"""Read-only native save/restore evidence audit. Never launches native/CUDA."""
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent.parent
sys.path.insert(0,str(ROOT/'strategic-vector-v1'))
from collect_vector import audit_native_events
import torch

def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def lines(path): return [json.loads(line) for line in Path(path).read_text().splitlines()]

prep=read(HERE/'PREPARATION.json')
result=read(HERE/'restore-run/result.json')
plan=read(HERE/'restore-run/plan.json')
original_agent=Path(prep['original_agent'])
original=read(original_agent/'smoke-result.json')['native_result']
restored=result['restored']
restored_agent=Path(restored['config']['agent_dir'])
runs=[]
pair_evidence=[]
for index in range(1,118):
    item={'index':index}
    for prefix in ('request','action'):
        a=original_agent/f'{prefix}-{index:08d}.json'
        b=restored_agent/a.name
        item[prefix]={'original_sha256':sha(a),'restored_sha256':sha(b),'bytes_equal':a.read_bytes()==b.read_bytes()}
    pair_evidence.append(item)
for label,native,agent in [('fresh',original,original_agent),('restore',restored,restored_agent)]:
    run=Path(native['run_dir'])
    requests=sorted(agent.glob('request-????????.json'))
    actions=sorted(agent.glob('action-????????.json'))
    last={'request':read(requests[-1]),'action':int(actions[-1].read_text())}
    native_audit=audit_native_events(run,len(requests),native['completed'],last)
    trace=lines(run/'strategy-trace.jsonl')
    terminal_indices=[i for i,r in enumerate(trace) if r['event'] in ('victory','defeat')]
    runs.append({'label':label,'agent_dir':str(agent),'native_dir':str(run),
        'request_count':len(requests),'action_count':len(actions),'native_audit':native_audit,
        'trace_records':len(trace),'trace_event_counts':dict(__import__('collections').Counter(r['event'] for r in trace)),
        'terminal_indices':terminal_indices,'postterminal_records':trace[terminal_indices[-1]+1:] if terminal_indices else [],
        'barrier_marker_count':(run/'client.log').read_text(errors='replace').count('Adventure battle barrier ready for player'),
        'client_log_sha256':sha(run/'client.log'),'inputs_unchanged':native['inputs_unchanged'],
        'winner':native['winner'],'day':native['turns']})
hashes=dict(prep['frozen_hashes']);hashes.update(plan['hashes'])
changed=[p for p,h in hashes.items() if not Path(p).is_file() or sha(p)!=h]
checkpoint=Path(next(p for p in hashes if p.endswith('threat-supply-clean-prior-v3.pt')))
bundle=torch.load(checkpoint,map_location='cpu',weights_only=False)
prior_fields={k:bundle.get(k) for k in ('trained','training_updates','optimizer_steps_total','optimizer')}
assert all(r['native_audit']['valid'] and r['native_audit']['missing_ack_count']==0 and r['native_audit']['missing_execution_reply_count']==0 for r in runs)
assert all(e[p]['bytes_equal'] for e in pair_evidence for p in ('request','action'))
assert result['passed'] and prep['preparation_passed'] and not changed
report={'passed':True,'scope':'CPU fresh new-policy native first-own-turn save/restore; no active battle; not PPO/CUDA recovery or independent ability improvement',
    'optimizer_steps_executed':0,'cuda_or_game_launched_by_audit':False,'checkpoint_sha256':sha(checkpoint),
    'prior_metadata':prior_fields,'runs':runs,'pair_evidence':pair_evidence,
    'trace_byte_comparisons':result['comparisons'],'frozen_hashes':hashes,'changed_frozen_paths':changed,
    'resource_release_probe_before_parent_handoff':{'pool_lock':'NB free','gpu_learner_lock':'NB free','owned_token_processes':[],
        'note':'Observed immediately after restore, before notifying parent to begin GPU work; this audit does not reserve or probe those resources again.'},
    'audit_sha256':sha(Path(__file__))}
(HERE/'AUDIT.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'passed':True,'runs':[{k:v for k,v in r.items() if k not in ('trace_event_counts','postterminal_records')} for r in runs],
    'prior_metadata':prior_fields,'changed_frozen_paths':changed},indent=2))
