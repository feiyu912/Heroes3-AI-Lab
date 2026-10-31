"""Restart failed supervisors only, preserving completed stages and checkpoints."""
import json
from pathlib import Path
import subprocess
import time
from lab_io import atomic_json


def running(name):
    result=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:args=(entry/'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError,PermissionError,ProcessLookupError):continue
        if len(args)>1 and Path(args[1].decode()).name==name:result.append(int(entry.name))
    return result


def main():
    r=Path(__file__).resolve().parent;stamp=str(time.time_ns())
    assert not (r/'final-policy-freeze.json').exists() and not list(r.glob('fresh-*-vs-*.json')),'Final policy already frozen: preserve that selection and resume final stages only, not model selection'
    control=json.loads((r/'goal-v5-control.json').read_text())
    assert control['state']=='failed','Recovery is only for an authoritative failure'
    for name in ['run-goal-v5.py','resume-paused-challenge.py','select-challenge-final.py',
                 'train-graph-finetune.py','train-recovered-heads.py','verify-live-training-resume.py']:
        assert not running(name),f'{name} still live; do not duplicate'
    assert json.loads((r/'central-opponent-cuda-deterministic-contract.json').read_text())['passed']
    assert json.loads((r/'full-graph-cuda-recompute-contract.json').read_text())['deterministic_rollout_batch_exact']
    progress=json.loads((r/'challenge24-pipeline-progress.json').read_text())
    successful=[]
    for row in progress:
        if row['returncode']!=0:break
        successful.append(row)
    assert len(successful)>=3
    atomic_json(r/f'challenge24-pipeline-progress-failure-{stamp}.json',progress)
    atomic_json(r/f'goal-v5-control-failure-{stamp}.json',control)
    contract=r/'live-training-resume-contract.json'
    if contract.exists():atomic_json(r/f'live-training-resume-before-recovery-{stamp}.json',json.loads(contract.read_text()))
    atomic_json(r/'challenge24-pipeline-progress.json',successful)
    atomic_json(r/'goal-v5-control.json',dict(state='recovering',updated_unix=time.time(),
        reason='Deterministic CUDA graph sums and rollout-shaped PPO recomputation; restore saved update112, retain all completed experiments.'))
    children=[]
    for script,python in [('run-goal-v5.py','python3'),('resume-paused-challenge.py','python3'),
                          ('verify-live-training-resume.py','/root/heroes3-ai-lab/venv/bin/python')]:
        log=r/(Path(script).stem+'-recovery-'+stamp+'.log')
        with log.open('wb') as stream:
            process=subprocess.Popen([python,str(r/script)],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        children.append(dict(script=script,pid=process.pid,log=str(log)))
    atomic_json(r/'goal-v5-recovery-status.json',dict(started_unix=time.time(),children=children,
        successful_stages_preserved=len(successful),reason='Verified numerical-recomputation repair'))
    print(json.dumps(children,indent=2),flush=True)


if __name__=='__main__':main()
