"""Finish the authorized challenge at24, one GPU trainer at a time."""
import json
from pathlib import Path
import subprocess
import time

r=Path('/mnt/g/Heroes3-AI-Lab/research')
jobs=[('/root/heroes3-ai-lab/venv/bin/python','continue-challenge-at24.py'),
      ('python3','finish-challenge-training.py'),
      ('python3','run-recovered-head-adaptation.py'),
      ('python3','select-challenge-final.py'),
      ('python3','run-fresh-challenge-evaluation.py')]
results=[]
for python,file in jobs:
    started=time.monotonic()
    with (r/(file.replace('.py','')+'-pipeline.log')).open('wb') as log:
        process=subprocess.run([python,str(r/file)],stdout=log,stderr=subprocess.STDOUT,timeout=14400)
    results.append(dict(script=file,returncode=process.returncode,wall_seconds=time.monotonic()-started))
    (r/'challenge24-pipeline-progress.json').write_text(json.dumps(results,indent=2))
    assert process.returncode==0,f'{file} failed, full log preserved'
    print(file,'completed',flush=True)
print('24-ENV CHALLENGE PIPELINE COMPLETE',flush=True)
