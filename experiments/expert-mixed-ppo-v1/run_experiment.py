"""Prepare/freeze explicitly; root alone schedules --run under shared flock."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from common import HERE,RESEARCH,PUBLIC,read,digest,prepare_plan,verify_plan
from lab_io import atomic_json


def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--prepare-only',action='store_true')
    mode.add_argument('--freeze-plan',action='store_true')
    mode.add_argument('--run',action='store_true')
    parser.add_argument('--plan')
    parser.add_argument('--checkpoint',help='Explicit initial weights for a new plan; never load their old optimizer')
    parser.add_argument('--reference-checkpoint',help='Independent anchor; default original public. Does not change historical opponent ONNX')
    parser.add_argument('--learning-rate',type=float,default=1e-5)
    parser.add_argument('--resume-checkpoint')
    args=parser.parse_args()
    path=Path(args.plan).resolve() if args.plan else HERE/('experiment-plan.json' if args.run or args.freeze_plan else 'draft-plan.json')
    assert path.is_relative_to(HERE) and path.suffix=='.json'
    if not args.run:
        plan=prepare_plan(path,args.checkpoint or PUBLIC,finalized=args.freeze_plan,learning_rate=args.learning_rate,reference_checkpoint=args.reference_checkpoint or PUBLIC)
        verify_plan(plan)
        print(json.dumps(dict(prepared=True,finalized_for_execution=plan['finalized_for_execution'],plan=str(path),training_started=False)),flush=True)
        return
    plan=read(path);verify_plan(plan)
    assert plan['finalized_for_execution'], 'Root must explicitly freeze final initialization/configuration first'
    if args.checkpoint:assert args.checkpoint==plan['initial_checkpoint'], 'Cannot change initialization after plan freeze'
    if args.reference_checkpoint:assert args.reference_checkpoint==plan['reference_checkpoint'], 'Cannot change reference after plan freeze'
    check=read(HERE/'cpu-preflight.json')
    assert check['passed'] and check['plan_sha256']==digest(path), 'Run CPU preflight against this exact final plan before --run'
    folder=HERE/path.stem;folder.mkdir(exist_ok=True)
    output=folder/'training.json'
    if output.exists():
        prior=read(output)
        assert prior['plan_sha256']==digest(path)
        if prior.get('completed'):
            assert prior['all_workers_exit_zero'] and digest(prior['checkpoint'])==prior['checkpoint_sha256']
            print('Matching mixed pilot already completed',flush=True);return
        assert args.resume_checkpoint and args.resume_checkpoint==prior['checkpoint'], 'Explicit saved checkpoint required for partial recovery'
        backup=output.with_name(output.name+'.before-resume-'+str(time.time_ns()))
        backup.write_bytes(output.read_bytes())
    lock_path=Path('/root/heroes3-ai-lab/evaluations/.pool-lock')
    with lock_path.open('a') as lock:
        atomic_json(folder/'control.json',dict(state='waiting_for_resource_lock',training_started=False))
        fcntl.flock(lock,fcntl.LOCK_EX)
        verify_plan(plan)
        atomic_json(folder/'control.json',dict(state='training',workers=24,updates=32))
        command=['bash',str(RESEARCH/'run-lab.sh'),str(HERE/'train_mixed_heads.py'),
            '--plan',str(path),'--output',str(output),'--lock-fd',str(lock.fileno())]
        if args.resume_checkpoint:command.extend(['--resume-checkpoint',args.resume_checkpoint])
        with (folder/'training.log').open('ab') as log:
            subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,pass_fds=(lock.fileno(),),
                env=dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python',LAB_STAGED_BOOT='1',
                         LAB_WORKER_ROOT='/root/heroes3-ai-lab/workers/expert-mixed-controller'))
    report=read(output)
    assert report.get('completed') and report.get('all_workers_exit_zero')
    assert digest(report['checkpoint'])==report['checkpoint_sha256']
    atomic_json(folder/'control.json',dict(state='training_complete',independent_confirmation_run=False,goal_achieved=False))


if __name__=='__main__':
    try:main()
    except BaseException as error:
        atomic_json(HERE/'controller-failure.json',dict(state='repair_needed',error=repr(error),goal_achieved=False))
        raise
