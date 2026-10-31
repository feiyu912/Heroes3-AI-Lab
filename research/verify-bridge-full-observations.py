"""Strengthen both bridge contracts before enabling the capacity benchmark."""
import json
import os
from pathlib import Path
import subprocess
import time
from lab_io import atomic_json

r=Path('/mnt/g/Heroes3-AI-Lab/research')
for device in ['cpu','cuda']:
    filename='central-opponent-cuda-contract.json' if device=='cuda' else 'central-opponent-contract.json'
    path=r/filename
    if path.exists() and json.loads(path.read_text()).get('observation_hash_version')!=2:
        path.rename(path.with_name(path.stem+'-node-digest-only-'+str(time.time_ns())+'.json'))
    python='/root/heroes3-ai-lab/gpu-venv/bin/python' if device=='cuda' else '/root/heroes3-ai-lab/venv/bin/python'
    with (r/f'central-full-observation-{device}.log').open('wb') as log:
        result=subprocess.run(['bash',str(r/'run-lab.sh'),str(r/'test-central-opponent.py'),'--device',device],
            stdout=log,stderr=subprocess.STDOUT,timeout=600,env=dict(os.environ,LAB_PYTHON=python))
    assert result.returncode==0,f'{device}: inspect full observation log'
    contract=json.loads(path.read_text());assert contract['passed'] and contract['observation_hash_version']==2
    print(device,'complete graph contract passed',flush=True)
atomic_json(r/'v5-boundary-ready.json',dict(ready=True,complete_graph_contracts=True,
    goal_selection_plan=str(r/'goal-selection-plan.json')))
