"""Measure native CUDA opponents while the experiment supervisor is stopped.

Let the currently running evaluation finish, benchmark sequentially, and always
resume the supervisor. No other learner/evaluator runs concurrently with probes.
"""
import json
import os
from pathlib import Path
import signal
import statistics
import subprocess
import time
from native_cuda_env import environment

r=Path('/mnt/g/Heroes3-AI-Lab/research')


def table():
    result={}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            args=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
            status=(p/'status').read_text().splitlines()
            parent=int(next(l.split()[1] for l in status if l.startswith('PPid:')))
            state=next(l.split()[1] for l in status if l.startswith('State:'))
            result[int(p.name)]=(parent,state,args)
        except (OSError,StopIteration):pass
    return result


current=table()
supervisors=[pid for pid,(_,_,args) in current.items() if str(r/'run-goal-v5.py') in args]
assert len(supervisors)==1
supervisor=supervisors[0]
assert not any(str(r/'train-recovered-heads.py') in args or str(r/'train-graph-finetune.py') in args for _,_,args in current.values())
os.kill(supervisor,signal.SIGSTOP)
results=[]
try:
    print('Stopped extended experiment supervisor; waiting for its evaluation to finish',flush=True)
    deadline=time.monotonic()+1800
    while True:
        current=table();children={supervisor}
        while True:
            new={pid for pid,(parent,_,_) in current.items() if parent in children}
            if new<=children:break
            children|=new
        active=[pid for pid in children-{supervisor} if current[pid][1]!='Z']
        if not active:break
        assert time.monotonic()<deadline,'Evaluation did not finish before benchmark'
        time.sleep(2)
    assert json.loads((r/'native-cuda-contract.json').read_text())['passed']
    for repeat in range(2):
        for cuda in [False,True]:
            name=f'v5-native-opponent-{"cuda" if cuda else "cpu"}-{repeat}'
            env=environment() if cuda else dict(os.environ)
            env.update(LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',LAB_STAGED_BOOT='1')
            output=r/(name+'.json')
            command=['bash',str(r/'run-lab.sh'),str(r/'train-recovered-heads.py'),'--workers','24',
                '--updates','4','--rollout','8','--checkpoint','/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt',
                '--scenario-file',str(r/'diverse-curriculum.json'),'--balanced-configs',
                '--seed',str(20261031+repeat),'--opponents','BattleAI','MMAI_MODEL','--output',str(output)]
            tick=time.monotonic()
            with (r/(name+'.log')).open('wb') as log:
                process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=1800)
            result=dict(cuda_opponent=cuda,repeat=repeat,workers=24,returncode=process.returncode,wall_seconds=time.monotonic()-tick,probe_excluded=True)
            if process.returncode==0:
                data=json.loads(output.read_text());assert data['completed'] and data['all_workers_exit_zero']
                speed=statistics.median(x['steps_per_second'] for x in data['records'][1:])
                # Account for the measured startup cost at the formal 16-update,
                # 32-step rotation interval, rather than ignoring slow GPU boot.
                rollout_seconds=sum(192/x['steps_per_second'] for x in data['records'])
                boot=max(0.,result['wall_seconds']-rollout_seconds)
                result.update(warm_decisions_per_second=speed,startup_seconds=boot,
                    estimated_16update_wall_seconds=boot+16*24*32/speed,
                    maximum_gpu_mib=max(x.get('gpu_telemetry',{}).get('memory_used_mib',0) for x in data['records']))
            results.append(result)
            (r/'native-cuda-throughput.json').write_text(json.dumps(dict(completed=False,results=results),indent=2))
            print(result,flush=True)
            if process.returncode and cuda:break
        if any(x['returncode'] for x in results):break
    complete=len(results)==4 and all(x['returncode']==0 for x in results)
    cpu=statistics.median(x['estimated_16update_wall_seconds'] for x in results if not x['cuda_opponent'] and x['returncode']==0)
    gpu=statistics.median(x['estimated_16update_wall_seconds'] for x in results if x['cuda_opponent'] and x['returncode']==0) if complete else None
    result=dict(completed=True,results=results,use_cuda=bool(complete and cpu/gpu>=1.10),
        estimated_end_to_end_speedup=cpu/gpu if complete else None,
        selection='Require exact live-game contract, both repetitions complete, >=10% estimated end-to-end improvement, and memory guards; probe checkpoints never adopted')
    (r/'native-cuda-throughput.json').write_text(json.dumps(result,indent=2))
    print(result,flush=True)
finally:
    os.kill(supervisor,signal.SIGCONT)
    print('Extended experiment supervisor resumed',flush=True)
