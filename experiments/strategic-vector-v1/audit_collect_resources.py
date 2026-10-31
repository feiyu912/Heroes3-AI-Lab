"""Read-only post-run resource/concurrency peak audit; no process/lock/GPU access."""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(run):
    plan=json.loads((run/'plan.json').read_text())
    batch=json.loads((run/'batch.json').read_text())
    samples=[json.loads(line) for line in (run/'resources.jsonl').open()]
    inference=[json.loads(line) for line in (run/'inference-batches.jsonl').open()]
    native_pids={json.loads(path.read_text())['pid'] for path in run.glob('env-*/native-pid.json')}
    peaks=dict(native=0,workers=0,simultaneous_pairs=0,rss=0,pss=0,
               gpu_torch_allocated_sampled=0,gpu_torch_reserved_sampled=0,system_swap_used=0)
    witness=None
    for sample in samples:
        pids={p['pid'] for p in sample['processes']}
        native=len(pids&native_pids)
        workers=sum(p['pid']==p['group'] and p['pid'] not in native_pids for p in sample['processes'])
        peaks['native']=max(peaks['native'],native);peaks['workers']=max(peaks['workers'],workers)
        peaks['simultaneous_pairs']=max(peaks['simultaneous_pairs'],min(native,workers))
        peaks['rss']=max(peaks['rss'],sample['batch_rss'])
        peaks['pss']=max(peaks['pss'],sum(p.get('pss') or 0 for p in sample['processes']))
        gpu=sample.get('gpu_manager')or{}
        peaks['gpu_torch_allocated_sampled']=max(peaks['gpu_torch_allocated_sampled'],gpu.get('allocated',0))
        peaks['gpu_torch_reserved_sampled']=max(peaks['gpu_torch_reserved_sampled'],gpu.get('reserved',0))
        peaks['system_swap_used']=max(peaks['system_swap_used'],sample['memory']['SwapUsed'])
        if min(native,workers)>=plan['environments'] and witness is None:
            witness=dict(seconds=sample['seconds'],native_pids=sorted(pids&native_pids),
                worker_pids=sorted(p['pid'] for p in sample['processes'] if p['pid']==p['group'] and p['pid'] not in native_pids))
    return dict(run=str(run),schema=plan['schema'],checkpoint_sha256=plan['checkpoint_sha256'],
        policy_version=plan['policy_version'],environments=plan['environments'],jobs=plan['jobs'],
        inference_schedule=plan.get('inference_schedule','not recorded by historical collector'),
        status=batch['status'],accepted_samples=batch['accepted_samples'],wall_seconds=batch['wall_seconds'],
        optimizer_steps=batch['actual_optimizer_steps'],resource_samples=len(samples),inference_batches=len(inference),
        maximum_forward_batch=max((row['batch_size'] for row in inference),default=0),
        maximum_candidate_width=max((max(row['candidate_counts']) for row in inference),default=0),
        peaks=peaks,simultaneous_witness=witness,min_system_available=min(s['memory']['MemAvailable'] for s in samples),
        remaining_processes_report=batch['remaining_processes'],
        episode_native_gate_valid=[e.get('native_event_audit',{}).get('valid') for e in batch['episodes']],
        source_sha256={p.name:sha(p) for p in (run/'plan.json',run/'batch.json',run/'resources.jsonl',run/'inference-batches.jsonl')},
        limitations='Sampled process RSS/PSS excludes manager CPU RSS; global available RAM includes it. GPU fields are sampled Torch allocator values, not hardware total VRAM or an instantaneous CUDA peak. Outcomes here belong only to this recorded checkpoint/native/protocol; no new clean-prior score is inferred.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('Refuse overwrite')
    report=audit(a.run);a.out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
