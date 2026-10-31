"""Compare CPU/native and one centrally batched CUDA peer at a quiet boundary."""
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
from lab_io import atomic_json

r=Path('/mnt/g/Heroes3-AI-Lab/research')
for name in ['central-opponent-contract.json','central-opponent-cuda-contract.json']:
    assert json.loads((r/name).read_text())['passed']
results=[]
for repeat in range(2):
    for central in [False,True]:
        name=f'v5-central-peer-{"cuda" if central else "cpu"}-{repeat}'
        output=r/(name+'.json')
        command=['bash',str(r/'run-lab.sh'),str(r/'train-recovered-heads.py'),'--workers','24',
            '--updates','4','--rollout','8','--checkpoint','/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt',
            '--scenario-file',str(r/'diverse-curriculum.json'),'--balanced-configs','--first-battle',
            '--seed',str(20261101+repeat),'--opponents','BattleAI','MMAI_GPU' if central else 'MMAI_MODEL','--output',str(output)]
        tick=time.monotonic()
        with (r/(name+'.log')).open('wb') as log:
            process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=1200,
                env=dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',LAB_STAGED_BOOT='1'))
        record=dict(central_gpu=central,repeat=repeat,workers=24,returncode=process.returncode,
            wall_seconds=time.monotonic()-tick,probe_weights_excluded=True)
        if process.returncode==0:
            data=json.loads(output.read_text());assert data['completed'] and data['all_workers_exit_zero']
            speed=statistics.median(x['steps_per_second'] for x in data['records'][1:])
            boot=max(0.,record['wall_seconds']-sum(192/x['steps_per_second'] for x in data['records']))
            record.update(warm_decisions_per_second=speed,startup_seconds=boot,
                estimated_16update_wall_seconds=boot+16*768/speed,
                minimum_available_mib=min(x['free_mib'] for x in data['records']),
                maximum_gpu_allocated_mib=max(x['gpu_allocated_mib'] for x in data['records']))
            if central:record['peer']=data['records'][-1]['fixed_opponent']
        results.append(record)
        atomic_json(r/'central-opponent-throughput.json',dict(completed=False,use_central_gpu=False,results=results))
        print(record,flush=True)
        if process.returncode:break
    if any(x['returncode'] for x in results):break
complete=len(results)==4 and all(x['returncode']==0 for x in results)
cpu=statistics.median(x['estimated_16update_wall_seconds'] for x in results if not x['central_gpu'] and x['returncode']==0) if any(not x['central_gpu'] and x['returncode']==0 for x in results) else None
gpu=statistics.median(x['estimated_16update_wall_seconds'] for x in results if x['central_gpu'] and x['returncode']==0) if complete else None
result=dict(completed=True,results=results,use_central_gpu=bool(complete and cpu/gpu>=1.10),
    estimated_end_to_end_speedup=cpu/gpu if complete else None,
    criterion='Both repetitions complete at24 with memory reserve, live exact-trajectory contracts and >=10% amortized whole-loop improvement. Probe checkpoints excluded.',
    bootstrap='Both comparison modes start from first connected battle; final evaluation remains the original native CPU protocol')
atomic_json(r/'central-opponent-throughput.json',result)
print(result,flush=True)
