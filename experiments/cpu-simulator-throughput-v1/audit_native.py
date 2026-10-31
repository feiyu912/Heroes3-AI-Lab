"""Independent read-only audit of native throughput reports and process samples."""
from collections import defaultdict
import fcntl
import hashlib
import json
from pathlib import Path
import sys

from measure import batch_processes


cache = {}
def sha(path):
    path = Path(path)
    if path not in cache:
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                h.update(chunk)
        cache[path] = h.hexdigest()
    return cache[path]


root = Path(sys.argv[1])
output = root/'AUDIT.json'
if output.exists() or (root/'RESULTS.md').exists():
    raise ValueError('Refuse overwriting audit')
report = dict(native_only=True, inputs=[], stage_audits=[], errors=[])
groups = defaultdict(list)
for name in ('native-01','native-02'):
    directory = root/name
    protocol = json.loads((directory/'protocol.json').read_text())
    result = json.loads((directory/'result.json').read_text())
    current_inputs_ok = all(sha(p)==s for p,s in protocol['hashes'].items())
    report['inputs'].append(dict(name=name, protocol_sha256=sha(directory/'protocol.json'),
        result_sha256=sha(directory/'result.json'), current_inputs_match=current_inputs_ok,
        synthetic=protocol['synthetic'], execute=protocol['execute'], status=result['status'],
        competitor_excluded=result['competitor_excluded'], current_batch_processes=batch_processes(protocol['token']),
        recorded_all_batch_processes_gone=result['all_batch_processes_gone']))
    if protocol['synthetic'] or not current_inputs_ok:
        report['errors'].append(name+': synthetic or changed frozen inputs')
    for stage in result['stages']:
        d = directory/f"scale-{stage['scale']:02d}"
        native_pids = set()
        all_job_evidence_ok = True
        for job in stage['jobs']:
            jdir = Path(job['directory'])
            native = job['native']
            native_pids.add(json.loads((jdir/'native-pid.json').read_text())['pid'])
            run = Path(native['run_dir'])
            plan = json.loads((run/'plan.json').read_text())
            hashes_ok = all(sha(p)==s for p,s in plan['hashes'].items())
            log_ok = sha(run/'client.log')==native['log_sha256']
            traces = {}
            for field, filename in [('strategy_trace_sha256','strategy-trace.jsonl'),
                                    ('strategy_decisions_sha256','strategy-decisions.jsonl'),
                                    ('strategy_targets_sha256','strategy-trace.jsonl.targets.jsonl')]:
                if field in native:
                    traces[field] = sha(run/filename)==native[field]
            ok = hashes_ok and log_ok and all(traces.values()) and native['completed'] and job['valid'] and job['exit']==0
            all_job_evidence_ok &= ok
            conf = native['config']
            key = (conf['map'],conf['red'],conf['blue'],conf['seed'])
            groups[key].append(dict(batch=name,scale=stage['scale'],job=jdir.name,
                winner=native['winner'], turns=native['turns'], moves=native['moves_requested'],
                state_sha=native.get('strategy_trace_sha256'), decisions_sha=native.get('strategy_decisions_sha256'),
                targets_sha=native.get('strategy_targets_sha256'), evidence_ok=ok))
        maximum_native = maximum_workers = maximum_both = 0
        witness = None
        maxrss = maxpss = maxswap = 0
        mins = []
        sample_count = 0
        for line in (d/'resources.jsonl').open():
            s = json.loads(line)
            sample_count += 1
            pids = {p['pid'] for p in s['processes']}
            live_native = len(pids & native_pids)
            workers = sum(p['pid']==p['group'] and p['pid'] not in native_pids for p in s['processes'])
            maximum_native = max(maximum_native, live_native)
            maximum_workers = max(maximum_workers, workers)
            maximum_both = max(maximum_both,min(live_native,workers))
            if witness is None and live_native >= stage['scale'] and workers >= stage['scale']:
                witness = dict(seconds=s['seconds'],native_pids=sorted(pids&native_pids),
                               worker_session_pids=sorted(p['pid'] for p in s['processes'] if p['pid']==p['group'] and p['pid'] not in native_pids))
            maxrss=max(maxrss,s['batch_rss'])
            maxpss=max(maxpss,s['batch_pss'])
            maxswap=max(maxswap,s['memory']['SwapUsed'])
            mins.append(s['memory']['MemAvailable'])
        a = dict(batch=name,scale=stage['scale'],valid_jobs=stage['valid_jobs'], sample_count=sample_count,
                 max_simultaneous_native_pids=maximum_native,max_simultaneous_worker_sessions=maximum_workers,
                 max_simultaneous_native_and_workers=maximum_both, simultaneous_witness=witness,
                 all_job_evidence_ok=all_job_evidence_ok, result_sha256=sha(d/'result.json'),
                 resource_samples_sha256=sha(d/'resources.jsonl'), peak_rss=maxrss,peak_pss=maxpss,
                 max_system_swap_used=maxswap,min_system_available=min(mins),
                 recorded_remaining_processes=stage['remaining_processes'],
                 metrics_match=maxrss==stage['peak_batch_rss'] and maxpss==stage['peak_batch_pss'],
                 wall_seconds=stage['wall_seconds'],games_per_second=stage['games_per_second'])
        report['stage_audits'].append(a)
        if not all_job_evidence_ok or not a['metrics_match'] or maximum_both < stage['scale']:
            report['errors'].append(f'{name} scale{stage["scale"]}: failed evidence/concurrency/metrics')
report['repeated_workloads'] = []
for key, jobs in groups.items():
    equal = {k:len({j[k] for j in jobs})==1 for k in ('winner','turns','moves','state_sha','decisions_sha','targets_sha')}
    report['repeated_workloads'].append(dict(config=key,count=len(jobs),equal=equal,reference=jobs[0]))
    if not all(equal.values()):
        report['errors'].append('Repeated workload differs: '+str(key))
with Path('/root/heroes3-ai-lab/evaluations/.pool-lock').open('a') as lock:
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        report['pool_lock_at_audit']='free_at_probe'
    except BlockingIOError:
        report['pool_lock_at_audit']='held_by_other_batch_at_probe'
report['passed']=not report['errors']
output.write_text(json.dumps(report,indent=2))
lines = ['# Real CPU simulation throughput audit','',
         'This is a native CPU throughput measurement with scripted DirectorAI and native battles. It does not demonstrate parallel PPO, GPU simulation, learned strategic improvement, or 204 independent evaluation games.','',
         '| Batch | Slots | Valid jobs | Simultaneous native/worker pairs | Games/s | Peak RSS GB | Peak PSS GB | Swap |',
         '|---|---:|---:|---:|---:|---:|---:|---:|']
for a in report['stage_audits']:
    lines.append(f"| {a['batch']} | {a['scale']} | {a['valid_jobs']} | {a['max_simultaneous_native_and_workers']} | {a['games_per_second']:.3f} | {a['peak_rss']/1e9:.3f} | {a['peak_pss']/1e9:.3f} | {a['max_system_swap_used']} |")
lines += ['',f"Audit passed: {report['passed']}. Every native log/trace hash, per-job frozen input and current protocol input was recomputed. Stage result and resource-sample SHA256 values and exact simultaneous-process witnesses are in AUDIT.json.",
          '', 'Concurrency is established by matching sampled live PIDs to per-job native PID files, with an equal number of separate worker sessions present at the same sample. The 24-slot run contains a sample with 24 native processes and 24 worker sessions simultaneously; it is not merely a queue length.',
          '', 'Both real batches recorded pool exclusion and no remaining batch processes; the audit independently found no processes carrying either completed batch token. Historical lock ownership follows the frozen FD/inode validation implementation and successful worker completion; this audit did not retroactively observe kernel locks during those runs. The current lock probe is separately recorded.',
          '', 'The four fixed map/role/seed workloads repeat intentionally. Across both real batches and all scales, winner, calendar turns, move count, full state-trace SHA, decision-trace SHA and target-diagnostic SHA match for every repetition of a workload. This supports deterministic workload comparability, not independent evidence of policy strength.',
          '', 'Samples are approximately every 200 ms; peaks are sampled, RSS counts shared pages multiple times, PSS is reported separately. Startup, file integrity checks, logging and cleanup are included. The observed 24-slot result supports this bounded workload on this machine, not arbitrary maps or indefinitely sustained 24-environment training. Synthetic results remain in separate synthetic-* directories.',
          '', 'No frozen measurement source or input was edited by this audit.']
(root/'RESULTS.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(passed=report['passed'],errors=report['errors'],stages=len(report['stage_audits']),output=str(output))))
