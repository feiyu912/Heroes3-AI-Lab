"""Wait for the frozen old suite, then train one isolated 24-worker pilot."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import time
from lab_io import atomic_json
from evaluation_provenance import digest

HERE=Path(__file__).resolve().parent
RESEARCH=HERE.parents[1]/'research'
INITIAL='/root/heroes3-ai-lab/models/recovered-v15/initial-pair.pt'
STATUS=HERE/'control.json'


def run(command,log,gpu=False):
    with (HERE/log).open('ab') as stream:
        subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=7200,
            env=dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python' if gpu else '/root/heroes3-ai-lab/venv/bin/python',
                     LAB_STAGED_BOOT='1',LAB_WORKER_ROOT='/root/heroes3-ai-lab/workers/conservative-controller'))


def main():
    plan=dict(initial=INITIAL,initial_sha256=digest(INITIAL),workers=24,updates=32,rollout=32,
        learning_rate=1e-5,reference_coef=0.1,gamma=1.0,step_cost=0.0,shaping=0.5,entropy_coef=0.005,
        train_cases='192 diverse ordinary mirrors, train only',
        development_cases='All 48 diverse development scenarios, both roles x2 seeds, 192 games/opponent',
        checkpoints=[16,32],opponents=['BattleAI','MMAI_GPU'],reference='Frozen original public pair, independently encoded observations',
        basis='Frozen v5 failed BattleAI target and regressed on defense; preserve public strategy while testing finite-win objective',
        old_final_results_read=True,old_final_results_used_for_selection=False,
        new_independent_confirmation_required=True,
        caveat='Combined method changes; not a single-factor KL ablation. Pilot result does not prove >=95% or beat author.')
    path=HERE/'experiment-plan.json'
    if path.exists():assert json.loads(path.read_text())==plan
    else:atomic_json(path,plan)
    while True:
        completion=json.loads((RESEARCH/'challenge-finalization-status.json').read_text(encoding='utf-8-sig'))
        assert completion['state']!='failed','Finish/repair the frozen old suite first'
        if completion['state']=='completed':break
        atomic_json(STATUS,dict(state='waiting_for_old_frozen_suite',old_pipeline_unchanged=True))
        time.sleep(30)
    check=json.loads((HERE/'cpu-math-check.json').read_text())
    assert check['passed'], 'Reference update contracts must pass before training'
    report=HERE/'training.json'
    if not report.exists():
        with Path('/root/heroes3-ai-lab/evaluations/.pool-lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            for entry in Path('/proc').iterdir():
                if not entry.name.isdigit():continue
                try:command=(entry/'cmdline').read_bytes().split(b'\0')
                except OSError:continue
                assert not (len(command)>1 and Path(os.fsdecode(command[1])).name in
                    ['train-graph-finetune.py','train-recovered-heads.py','train_conservative_heads.py']), 'Another unmanaged CUDA learner is active'
            atomic_json(STATUS,dict(state='training',workers=24,updates=32))
            run(['bash',str(RESEARCH/'run-lab.sh'),str(HERE/'train_conservative_heads.py'),
                '--checkpoint',INITIAL,'--workers','24','--updates','32','--rollout','32',
                '--learning-rate','1e-5','--reference-coef','.1','--gamma','1','--step-cost','0',
                '--shaping','.5','--entropy-coef','.005','--seed','2026101602','--balanced-configs',
                '--opponents','BattleAI','MMAI_GPU','--scenario-file',str(RESEARCH/'diverse-curriculum.json'),
                '--output',str(report)],'training.log',True)
    trained=json.loads(report.read_text())
    assert trained['completed'] and trained['all_workers_exit_zero'] and trained['CUDA_training']
    candidates=[('public-original',INITIAL),('conservative-16',str(Path(trained['checkpoint']).with_name('update-16.pt'))),
                ('conservative-32',trained['checkpoint'])]
    results=[]
    for name,checkpoint in candidates:
        row=dict(name=name,checkpoint=checkpoint,checkpoint_sha256=digest(checkpoint))
        for opponent in ['BattleAI','MMAI_MODEL']:
            output=HERE/f'{name}-{opponent}-development.json'
            atomic_json(STATUS,dict(state='expanded_development_validation',candidate=name,opponent=opponent,scenarios=48))
            command=['python3',str(RESEARCH/'evaluate-battles.py'),'--checkpoint',checkpoint,'--policies','recovered',
                '--scenario-file',str(RESEARCH/'diverse-curriculum.json'),'--scenarios',*map(str,range(192,240)),
                '--seeds','2','--workers','12','--opponent',opponent,'--output',str(output)]
            if opponent=='MMAI_MODEL':command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
            run(command,output.stem+'.log')
            data=json.loads(output.read_text())
            assert data['summary'][0]['battles']==192 and data['summary'][0]['invalid_actions']==0
            row[opponent]=dict(report=str(output),summary=data['summary'][0])
        results.append(row)
        atomic_json(HERE/'development-results.json',results)
    atomic_json(STATUS,dict(state='pilot_development_complete',independent_confirmation_run=False,
        goal_achieved=False,scope='Method pilot only. Inspect actual expanded development results before further training or new frozen confirmation.'))


if __name__=='__main__':
    try:main()
    except BaseException as error:
        atomic_json(STATUS,dict(state='failed',error=repr(error),old_pipeline_unchanged=True))
        raise
