"""Benchmark between trainers, so measurements do not compete with an active job."""
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import time

r=Path('/mnt/g/Heroes3-AI-Lab/research')
coordinators=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit(): continue
    try:
        arguments=(proc/'cmdline').read_bytes().split(b'\0')
        if len(arguments)>1 and arguments[1]==str(r/'run-challenge-training.py').encode():
            coordinators.append(int(proc.name))
    except (FileNotFoundError,PermissionError): pass
assert len(coordinators)==1,coordinators
coordinator=coordinators[0]
# Stop only the queue supervisor. Its active trainer continues to finish normally.
os.kill(coordinator,signal.SIGSTOP)
print('Queue held between jobs; active trainer continues',flush=True)
results=[]
try:
    deadline=time.monotonic()+7200
    while True:
        data=json.loads((r/'linked-v4-battleai.json').read_text())
        if data.get('completed'): break
        assert time.monotonic()<deadline,'Active trainer exceeded bounded wait'
        time.sleep(3)
    # Let the last worker shutdown and trainer process exit before measuring.
    time.sleep(3)
    validation=str(r/'linked-v4-initial-validation.json')
    checkpoint='/root/heroes3-ai-lab/models/linked-v4/initial.pt'
    capacity_failed = False
    for workers in [12,16,20,24,32,40,48]:
        if capacity_failed:
            results.append(dict(workers=workers,failed=True,not_started=True,
                                reason='Smaller configuration already hit resource/startup guard; larger count not safe in current WSL memory limit'))
            continue
        for repeat in range(2):
            output=r/f'challenge-speed-{workers}-{repeat}.json'
            command=['bash',str(r/'run-lab.sh'),str(r/'train-ppo.py'),'--workers',str(workers),'--rollout','32',
                '--updates','8','--epochs','3','--batch-size','64','--seed','20261017','--checkpoint',checkpoint,
                '--validation-report',validation,'--scenarios',str(r/'scenarios-v2.json'),
                '--inference-device','cuda','--training-device','cuda','--cache-next-value',
                '--fixed-map','lab/balanced-10.vmap','--fixed-role','attacker','--output',str(output)]
            with output.with_suffix('.log').open('wb') as log:
                process=subprocess.run(command,env=dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',LAB_STAGED_BOOT='1'),
                    stdout=log,stderr=subprocess.STDOUT,timeout=600)
            if process.returncode:
                results.append(dict(workers=workers,repeat=repeat,failed=True,returncode=process.returncode))
                capacity_failed=True
                break
            data=json.loads(output.read_text());assert data['completed'] and data['all_workers_exit_zero']
            times=[x['effective_steps_per_second'] for x in data['records'][2:]]
            results.append(dict(workers=workers,repeat=repeat,failed=False,steps_per_second=statistics.median(times),
                peak_pss_mib=data['sampled_peak_total_pss_mib'],minimum_free_mib=min(x['wsl_min_available_mib'] for x in data['records']),
                swap_mib=max(x['wsl_max_swap_used_mib'] for x in data['records'])))
            (r/'challenge-concurrency-results.json').write_text(json.dumps(dict(results=results,completed=False),indent=2))
    valid={n:statistics.median(x['steps_per_second'] for x in results if x['workers']==n and not x['failed'])
        for n in [12,16,20,24,32,40,48] if len([x for x in results if x['workers']==n and not x['failed']])==2}
    best=max(valid,key=valid.get)
    # Prefer smaller configurations within 5% of the fastest measured rate.
    recommended=min(n for n in valid if valid[n]>=valid[best]*0.95)
    report=dict(results=results,completed=True,medians=valid,recommended_workers=recommended,
                fixture='Same linked model and real three-stack balanced-10 battle, CPU rules, GPU inference/update; two repetitions, warm first two updates omitted',
                selection='Smallest tested count within 5% of fastest; no memory/swap/worker failures accepted')
    (r/'challenge-concurrency-results.json').write_text(json.dumps(report,indent=2))
    print(report,flush=True)
finally:
    # Resume the original queue even if a benchmark fails.
    os.kill(coordinator,signal.SIGCONT)
    print('Original training queue resumed',flush=True)
