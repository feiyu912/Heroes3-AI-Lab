"""Resume only the paused third stage, then validation and untouched final holdout."""
import json
from pathlib import Path
import subprocess
import time

r=Path('/mnt/g/Heroes3-AI-Lab/research')
paused=json.loads((r/'challenge-paused-state.json').read_text())
assert paused['status'] in ['paused_for_user_shutdown','checkpoint_recovery']
progress=json.loads((r/'challenge24-pipeline-progress.json').read_text())
assert len(progress)>=2 and all(x['returncode']==0 for x in progress[:2])
failed=next((i for i,row in enumerate(progress) if row['returncode']!=0),None)
if failed is not None:
    (r/f'challenge24-pipeline-progress-failure-{time.time_ns()}.json').write_text(json.dumps(progress,indent=2))
    progress=progress[:failed]
    (r/'challenge24-pipeline-progress.json').write_text(json.dumps(progress,indent=2))
jobs=[('run-recovered-head-adaptation.py',['--resume-paused']),
      ('select-challenge-final.py',[]),('run-fresh-challenge-evaluation.py',[])]
for script,args in jobs:
    completed=next((row for row in progress if row['script']==script),None)
    if completed:
        assert completed['returncode']==0
        print(script,'already completed; preserved',flush=True)
        continue
    tick=time.monotonic()
    logfile=r/(script.removesuffix('.py')+'-resume.log')
    if logfile.exists():logfile.rename(logfile.with_name(logfile.name+'.previous-'+str(time.time_ns())))
    with logfile.open('wb') as log:
        result=subprocess.run(['python3',str(r/script),*args],stdout=log,stderr=subprocess.STDOUT,timeout=86400)
    progress.append(dict(script=script,returncode=result.returncode,wall_seconds=time.monotonic()-tick,resumed=True))
    (r/'challenge24-pipeline-progress.json').write_text(json.dumps(progress,indent=2))
    assert result.returncode==0,f'{script} failed; log preserved'
    print(script,'completed',flush=True)
