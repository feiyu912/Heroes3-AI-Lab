"""Avoid running the one-worker bridge check alongside midpoint evaluation."""
import json
from pathlib import Path
import subprocess
import time
import os

r=Path('/mnt/g/Heroes3-AI-Lab/research')
while True:
    state=json.loads((r/'v5-midpoint-status.json').read_text())
    if state['state'] in ['completed','failed']:break
    time.sleep(20)
with (r/'central-opponent-bootstrap-check.log').open('wb') as log:
    result=subprocess.run(['bash',str(r/'run-lab.sh'),str(r/'test-central-opponent.py')],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
print('Bootstrap-aligned central opponent check completed',result.returncode,flush=True)
assert result.returncode==0,'Inspect central-opponent-bootstrap-check.log; formal pipeline remains unchanged'
assert json.loads((r/'central-opponent-contract.json').read_text())['passed']
with (r/'central-opponent-cuda-check.log').open('wb') as log:
    result=subprocess.run(['bash',str(r/'run-lab.sh'),str(r/'test-central-opponent.py'),'--device','cuda'],
        stdout=log,stderr=subprocess.STDOUT,timeout=1800,
        env=dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python'))
print('CUDA central opponent check completed',result.returncode,flush=True)
assert result.returncode==0,'Inspect central-opponent-cuda-check.log; formal pipeline remains unchanged'
