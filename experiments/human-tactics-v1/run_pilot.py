"""Serial independent pilot, sharing the existing simulator/GPU resource lock."""
import json
import os
from pathlib import Path
import subprocess
import time
from lab_io import atomic_json
from evaluation_provenance import digest

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1]/'research'
INITIAL = '/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt'
BC = HERE/'models/bc-policy.pt'


def execute(script, arguments, name, gpu=False):
    with (HERE/(name+'.log')).open('ab') as log:
        env = dict(os.environ, LAB_WORKER_ROOT='/root/heroes3-ai-lab/workers/human-pilot-'+name,
            LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python' if gpu else '/root/heroes3-ai-lab/venv/bin/python')
        subprocess.run(['bash', str(RESEARCH/'run-lab.sh'), str(HERE/script), *arguments],
            env=env, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=7200)


def episode(index, role, policy, checkpoint, label):
    cases = json.loads((HERE/'scenarios.json').read_text())
    case = cases[index]
    name = f'{label}-{case["tactic_id"]}-{case["split"]}-{index}-{role}'
    output = HERE/'runs'/(name+'.json')
    if output.exists():
        prior = json.loads(output.read_text())
        assert prior.get('completed'), f'Failed episode preserved: {output}'
        assert prior['checkpoint']==str(checkpoint) and prior['policy']==policy
        return prior
    execute('run_episode.py', ['--scenario',str(index),'--role',role,'--seed',str(2026102801+index*100),
        '--policy',policy,'--checkpoint',str(checkpoint),'--output',str(output)], name)
    assert output.exists(), f'Episode did not write authoritative result: {output}'
    result = json.loads(output.read_text())
    assert result.get('completed'), result
    return result


def main():
    results = []
    status = HERE/'pilot-control.json'
    for index in [0,1,8,9,16,17]:
        for role in ['attacker','defender']:
            for policy,label in [('expert','expert'),('model','baseline')]:
                atomic_json(status,dict(state='training_data_and_paired_baseline',scenario=index,role=role,policy=policy,
                    original_pipeline_unchanged=True))
                results.append(episode(index,role,policy,INITIAL,label))
                atomic_json(HERE/'pilot-training-battles.json',results)
    if not (HERE/'bc-training.json').exists():
        atomic_json(status,dict(state='waiting_for_resource_lock_then_BC',original_pipeline_unchanged=True))
        execute('train_bc.py',['--checkpoint',INITIAL,'--output',str(BC),'--steps','60'],'bc-training',True)
    assert json.loads((HERE/'bc-training.json').read_text())['completed']
    freeze = dict(checkpoint=str(BC),sha256=digest(BC), initial=INITIAL, initial_sha256=digest(INITIAL),
        frozen_unix=time.time(),test_results_read=False,selection='Fixed 60-step BC pilot, no test selection')
    freeze_path = HERE/'pilot-policy-freeze.json'
    if freeze_path.exists():
        previous = json.loads(freeze_path.read_text())
        assert previous['sha256']==freeze['sha256'] and previous['initial_sha256']==freeze['initial_sha256']
    else:
        atomic_json(freeze_path,freeze)
    heldout = []
    for index in [6,7,14,15,22,23]:
        for role in ['attacker','defender']:
            for checkpoint,label in [(INITIAL,'baseline'),(str(BC),'bc')]:
                assert digest(BC)==freeze['sha256'] and digest(INITIAL)==freeze['initial_sha256']
                atomic_json(status,dict(state='frozen_independent_tactical_test',scenario=index,role=role,policy=label,
                    original_pipeline_unchanged=True))
                heldout.append(episode(index,role,'model',checkpoint,label))
                atomic_json(HERE/'pilot-heldout-battles.json',heldout)
    groups = {}
    for label,checkpoint in [('baseline',INITIAL),('bc',str(BC))]:
        rows = [row for row in heldout if row['checkpoint']==checkpoint]
        groups[label] = dict(battles=len(rows),wins=sum(row['success'] for row in rows),
            truncations=sum(row['truncated'] for row in rows), invalid_actions=sum(row['invalid_actions'] for row in rows),
            mean_permanent_units_lost=sum(row['permanent_army_loss_units'] for row in rows)/len(rows),
            multi_target_opportunities=sum(row['multi_target_opportunities'] for row in rows),
            selected_multi_enemy_attacks=sum(row['selected_multi_enemy_attacks'] for row in rows))
    atomic_json(HERE/'pilot-comparison.json',dict(completed=True,groups=groups,
        limitations='Small pilot. Raw coverage is not certified tactic success. No human video traces, historical opponent pool or specialized counter expert trained. Ordinary-battle regression and PPO comparisons remain separate required follow-up.'))
    atomic_json(status,dict(state='completed_BC_pilot',original_pipeline_unchanged=True,
        full_human_curriculum_complete=False,expert_source_case_integrated=False))
    print(json.dumps(groups),flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        atomic_json(HERE/'pilot-control.json',dict(state='failed',error=repr(error),original_pipeline_unchanged=True))
        raise
