"""Finish active pilots, then execute the explicitly frozen B64 mixed experiment."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
RESEARCH=HERE.parent/'research'
sys.path.insert(0,str(RESEARCH))
from lab_io import atomic_json
from evaluation_provenance import digest

MIXED=HERE/'expert-mixed-ppo-v1'
PLAN=MIXED/'b64-anchor-plan.json'
OUT=HERE/'expert-mixed-b64-run-v1'
STATUS=OUT/'control.json'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def run(command,name,gpu=False):
    with (OUT/(name+'.log')).open('ab') as log:
        subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT,timeout=7200,
            env=dict(os.environ,LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python' if gpu else '/root/heroes3-ai-lab/venv/bin/python'))


def verify_evaluation(path,checkpoint,opponent):
    data=read(path)
    assert data['checkpoint']==checkpoint and data['opponent']==opponent
    assert data['scenario_file']==str(RESEARCH/'diverse-curriculum.json')
    assert data['scenario_ids']==list(range(192,240)) and data['workers']==12
    assert data['opponent_model_template']==('DATA/MMAI/models/lab-upstream-{role}.onnx' if opponent=='MMAI_MODEL' else None)
    assert data['artifacts_checked_before_and_after'] and data['frozen_artifacts'][checkpoint]==digest(checkpoint)
    rows=data['battles'];assert len(rows)==192
    expected={(f'diverse-{index:03d}',role,2026101400+index*100+seed)
        for index in range(192,240) for role in ['attacker','defender'] for seed in range(2)}
    assert {(row['scenario'],row['role'],row['seed']) for row in rows}==expected
    from battle_outcome_audit import audit
    audit(rows)
    summary=data['summary'][0]
    assert summary['battles']==192 and summary['wins']==sum(row['success'] for row in rows)
    assert summary['invalid_actions']==summary['truncated']==summary['non_normal_terminations']==0
    return summary


def main():
    OUT.mkdir(exist_ok=True)
    plan=read(PLAN)
    assert plan['finalized_for_execution'] and plan['initial_checkpoint']==plan['reference_checkpoint']
    assert plan['learning_rate']==1e-4 and plan['updates']==32 and plan['workers']==24
    assert read(MIXED/'cpu-preflight.json')['plan_sha256']==digest(PLAN)
    prerequisites=[
        dict(control=str(HERE/'human-tactics-recovery-v2/pilot-control.json'),done='completed_BC_pilot',pid=193903,script='run_pilot.py'),
        dict(control=str(HERE/'expert-knowledge-v1/wait-variant-v2/source-bc-control.json'),done='completed',pid=206353,script='train_source_wait.py'),
        dict(control=str(HERE/'expert-retention-v1/control.json'),done='development_retention_complete',pid=201423,script='run_retention.py')]
    manifest=dict(plan=str(PLAN),plan_sha256=digest(PLAN),controller_sha256=digest(__file__),
        evaluation_script_sha256=digest(RESEARCH/'evaluate-battles.py'),prerequisites=prerequisites,
        development_scenarios=list(range(192,240)),roles=2,seeds=2,opponents=['BattleAI','MMAI_MODEL'],
        candidates=['b64-baseline','mixed-16','mixed-32'],games_per_matchup=192,total_development_games=1152,
        independent_confirmation=False,new_confirmation_results_used=False)
    manifest_path=OUT/'orchestration-plan.json'
    if manifest_path.exists():assert read(manifest_path)==manifest
    else:atomic_json(manifest_path,manifest)
    while True:
        pending=[]
        for item in prerequisites:
            state=read(item['control']);label=state.get('state',state.get('status'))
            assert label not in ['failed','repair_needed','needs_repair'],str(item)+': '+str(state)
            if label!=item['done']:
                process=Path('/proc')/str(item['pid'])/'cmdline'
                assert process.exists() and item['script'].encode() in process.read_bytes(), 'Pending prerequisite has no matching live process: '+str(item)
                pending.append(dict(control=item['control'],state=label,pid=item['pid']))
        if not pending:break
        atomic_json(STATUS,dict(state='waiting_for_active_pilots',pending=pending,training_started=False))
        time.sleep(30)
    assert digest(PLAN)==manifest['plan_sha256'] and digest(__file__)==manifest['controller_sha256']
    run(['/root/heroes3-ai-lab/venv/bin/python',str(HERE/'report-expert-pilots.py')],'prior-pilot-results')
    atomic_json(STATUS,dict(state='launching_mixed_training',workers=24))
    run(['bash',str(RESEARCH/'run-lab.sh'),str(MIXED/'run_experiment.py'),'--run','--plan',str(PLAN)],'mixed-training')
    training=read(MIXED/'b64-anchor-plan/training.json')
    assert training['completed'] and training['CUDA_training'] and training['all_workers_exit_zero']
    assert training['plan_sha256']==manifest['plan_sha256']
    assert digest(training['checkpoint'])==training['checkpoint_sha256']
    candidates=[('b64-baseline',plan['initial_checkpoint']),
        ('mixed-16',str(Path(training['checkpoint']).with_name('update-16.pt'))),('mixed-32',training['checkpoint'])]
    results=[]
    for name,checkpoint in candidates:
        row=dict(name=name,checkpoint=checkpoint,checkpoint_sha256=digest(checkpoint))
        for opponent in manifest['opponents']:
            output=OUT/f'{name}-{opponent}-development.json'
            atomic_json(STATUS,dict(state='expanded_development_validation',candidate=name,opponent=opponent))
            if not output.exists():
                assert digest(RESEARCH/'evaluate-battles.py')==manifest['evaluation_script_sha256']
                command=['/root/heroes3-ai-lab/venv/bin/python',str(RESEARCH/'evaluate-battles.py'),
                    '--checkpoint',checkpoint,'--policies','recovered','--scenario-file',str(RESEARCH/'diverse-curriculum.json'),
                    '--scenarios',*map(str,range(192,240)),'--seeds','2','--workers','12','--opponent',opponent,'--output',str(output)]
                if opponent=='MMAI_MODEL':command+=['--opponent-model-template','DATA/MMAI/models/lab-upstream-{role}.onnx']
                run(command,output.stem)
            row[opponent]=dict(summary=verify_evaluation(output,checkpoint,opponent),report=str(output),sha256=digest(output))
        results.append(row)
        atomic_json(OUT/'development-results.json',dict(complete=False,results=results,goal_achieved=False))
    atomic_json(OUT/'development-results.json',dict(complete=True,results=results,goal_achieved=False,independent_confirmation=False))
    atomic_json(STATUS,dict(state='mixed_development_complete',goal_achieved=False,new_confirmation_required=True))


if __name__=='__main__':
    try:main()
    except BaseException as error:
        OUT.mkdir(exist_ok=True)
        atomic_json(STATUS,dict(state='repair_needed',error=repr(error),goal_achieved=False))
        raise
