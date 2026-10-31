"""Require identical CPU/GPU opponent trajectories and actual CUDA kernel traces."""
import json
import os
from pathlib import Path
import subprocess
import time
from native_cuda_env import environment

r=Path('/mnt/g/Heroes3-AI-Lab/research')
output=Path('/root/heroes3-ai-lab/evaluations')/('native-cuda-contract-'+str(time.time_ns()))
output.mkdir(parents=True)
records=[]
try:
    for role in ['attacker','defender']:
        for scenario in [0,7,14]:
            reports=[]
            for cuda in [False,True]:
                name=f'{role}-{scenario}-{int(cuda)}'
                result_path=output/(name+'.json')
                env=environment(profile=True,require_contract=False) if cuda else dict(os.environ)
                env['LAB_WORKER_ROOT']=f'/root/heroes3-ai-lab/workers/native-cuda-contract-{output.name}/{name}'
                command=['bash',str(r/'run-lab.sh'),str(r/'evaluate-policy.py'),'--scenario',str(scenario),
                    '--role',role,'--seed',str(2026101900+scenario),'--policy','recovered',
                    '--checkpoint','/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt',
                    '--scenarios',str(r/'scenarios-v2.json'),'--opponent','MMAI_MODEL',
                    '--opponent-model','DATA/MMAI/models/lab-upstream-'+('defender' if role=='attacker' else 'attacker')+'.onnx',
                    '--output',str(result_path)]
                with (output/(name+'.log')).open('wb') as log:
                    process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,env=env,timeout=300)
                assert process.returncode==0,f'{name} failed: {output/(name+".log")}'
                reports.append(json.loads(result_path.read_text()))
            assert all(x['terminated'] and not x['truncated'] and x['invalid_actions']==0 for x in reports)
            identical=(reports[0]['trajectory_sha256']==reports[1]['trajectory_sha256'] and reports[0]['terminal_outcome']==reports[1]['terminal_outcome'])
            records.append(dict(role=role,scenario=scenario,exact_trajectory=identical,
                CPU_wall_seconds=reports[0]['wall_seconds'],GPU_wall_seconds=reports[1]['wall_seconds']))
            print(records[-1],flush=True)
    profiles=[]
    for file in Path('/root/heroes3-ai-lab/profiles').glob('native-cuda-*.json'):
        events=json.loads(file.read_text())
        cuda=sum(e.get('args',{}).get('provider')=='CUDAExecutionProvider' for e in events)
        cpu=sum(e.get('args',{}).get('provider')=='CPUExecutionProvider' for e in events)
        profiles.append(dict(path=str(file),cuda_nodes=cuda,cpu_nodes=cpu))
    assert profiles and all(x['cuda_nodes']>0 for x in profiles),'CUDA execution not proven'
    passed=all(x['exact_trajectory'] for x in records)
    result=dict(passed=passed,all_exact_trajectories=passed,records=records,profiles=profiles,
        unchanged_engine_rules=True,TF32_disabled=True,scope='Six seeded battles, both roles; native CPU1.22 vs native CUDA1.23.2 opponent, same public weights and greedy policy',
        evaluation_folder=str(output))
    (r/'native-cuda-contract.json').write_text(json.dumps(result,indent=2))
    assert passed,'GPU arithmetic changed trajectories; exclude from formal use'
except BaseException as error:
    if (r/'native-cuda-failure.json').exists():
        (r/'native-cuda-failure.json').rename(r/('native-cuda-failure-'+str(time.time_ns())+'.json'))
    (r/'native-cuda-failure.json').write_text(json.dumps(dict(error=repr(error),records=records,evaluation_folder=str(output),formal_use=False),indent=2))
    raise
