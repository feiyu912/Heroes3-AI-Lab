"""Validate the frozen midpoint with one extra CPU worker; never read final tests.

This overlaps only a small diagnostic evaluator with a training stage.
The global evaluation lock prevents duplicate or simultaneous evaluator pools.
"""
import json
import argparse
import os
from pathlib import Path
import subprocess
import time
import zipfile
from lab_io import atomic_json

r=Path('/mnt/g/Heroes3-AI-Lab/research')
parser=argparse.ArgumentParser()
parser.add_argument('--training-report',default=str(r/'v5-diverse-heads.json'))
parser.add_argument('--target-update',type=int,default=128)
parser.add_argument('--name-prefix',default='v5-diverse-heads')
parser.add_argument('--status-file',default=str(r/'v5-midpoint-status.json'))
options=parser.parse_args()
training_report=Path(options.training_report).resolve()
status=Path(options.status_file)
try:
    while True:
        report=json.loads(training_report.read_text())
        candidates=[Path(report['checkpoint']).parent/f'update-{options.target_update}.pt']
        if report.get('source_snapshot'):candidates.append(Path(report['source_snapshot']).parent/f'update-{options.target_update}.pt')
        if str(options.target_update) in report.get('checkpoint_history',{}):candidates.append(Path(report['checkpoint_history'][str(options.target_update)]))
        checkpoint=next((path for path in candidates if path.is_file()),None)
        if checkpoint:
            try:
                with zipfile.ZipFile(checkpoint) as archive:assert archive.testzip() is None
                break
            except (zipfile.BadZipFile,AssertionError):pass
        live=[]
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():continue
            try:args=(proc/'cmdline').read_bytes().split(b'\0')
            except OSError:continue
            trainer=any(str(r/name).encode() in args for name in ['train-recovered-heads.py','train-graph-finetune.py'])
            if trainer and str(training_report).encode() in args:live.append(int(proc.name))
        assert live or report.get('completed'),'Training stopped before a saved midpoint'
        assert not report.get('completed'),'Completed training lacks requested saved midpoint'
        atomic_json(status,dict(state='waiting_for_midpoint',trainer_pids=live,target_update=options.target_update))
        time.sleep(30)
    for file,indices,seeds,prefix in [('scenarios-v2.json',range(20,26),4,''),('diverse-curriculum.json',range(192,204),2,'development_')]:
        for opponent,label in [('BattleAI',''),('MMAI_MODEL','upstream_')]:
            output=r/f'{options.name_prefix}-{options.target_update}-{prefix}{label}validation.json'
            if output.exists():continue
            # One evaluator needs substantially less than the spare 4 GiB;
            # leave at least 2 GiB for the existing learner and engine workers.
            while True:
                available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))
                if available>4096*1024:break
                time.sleep(15)
            atomic_json(status,dict(state='validating_midpoint',checkpoint=str(checkpoint),output=str(output),workers=1))
            command=['python3',str(r/'evaluate-battles.py'),'--checkpoint',str(checkpoint),'--policies','recovered',
                '--scenario-file',str(r/file),'--scenarios',*map(str,indices),'--seeds',str(seeds),
                '--workers','1','--opponent',opponent,'--output',str(output)]
            if opponent=='MMAI_MODEL':command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
            with output.with_suffix('.midpoint.log').open('wb') as log:
                process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=3600)
            assert process.returncode==0,f'{output.name}: inspect midpoint log'
            print(output.name,json.loads(output.read_text())['summary'][0],flush=True)
    atomic_json(status,dict(state='completed',checkpoint=str(checkpoint),final_test_not_read=True))
except BaseException as error:
    atomic_json(status,dict(state='failed',error=repr(error),final_test_not_read=True))
    raise
