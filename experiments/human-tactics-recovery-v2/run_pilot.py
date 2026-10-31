"""Resume fixed Q2 pilot using original frozen episodes and shape-safe BC."""
import json
import os
from pathlib import Path
import subprocess
import time
from lab_io import atomic_json
from recovery_utils import HERE,V1,RESEARCH,digest,read,training_rows,validate_episode,validate_bc,frozen_recovery

INITIAL = '/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt'
BC = V1/'models/bc-policy.pt'
CONTROL = HERE/'pilot-control.json'


def execute(script,arguments,name,gpu=False):
    with (HERE/(name+'.log')).open('ab') as log:
        env = dict(os.environ,LAB_WORKER_ROOT='/root/heroes3-ai-lab/workers/human-recovery-v2-'+name,
            LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python' if gpu else '/root/heroes3-ai-lab/venv/bin/python')
        subprocess.run(['bash',str(RESEARCH/'run-lab.sh'),str(script),*arguments],env=env,
            stdout=log,stderr=subprocess.STDOUT,check=True,timeout=7200)


def episode(index,role,checkpoint,label):
    case = read(V1/'scenarios.json')[index]
    name = f'{label}-{case["tactic_id"]}-{case["split"]}-{index}-{role}'
    output = V1/'runs'/(name+'.json')
    if not output.exists():
        execute(V1/'run_episode.py',['--scenario',str(index),'--role',role,'--seed',str(2026102801+index*100),
            '--policy','model','--checkpoint',str(checkpoint),'--output',str(output)],name)
    assert output.exists(), 'Exit status alone does not prove episode completion'
    return validate_episode(read(output),index,role,'model',checkpoint)


def main():
    manifest = read(HERE/'recovery-manifest.json')
    assert manifest['cpu_preflight_passed']
    assert digest(HERE/'cpu-preflight.json')==manifest['cpu_preflight_sha256']
    assert frozen_recovery()==manifest['recovery_artifacts'], 'Recovery code changed since CPU preflight'
    for path,sha in manifest['original_artifacts'].items():
        assert digest(path)==sha, 'Original evidence changed: '+path
    training_rows(INITIAL)  # Validate all 24; never collect or rewrite them.
    if (V1/'bc-training.json').exists():
        validate_bc(INITIAL,BC)
    else:
        assert not BC.exists(), 'Unreported model preserved; investigate before rerunning'
        atomic_json(CONTROL,dict(state='waiting_for_resource_lock_then_BC',original_pipeline_unchanged=True))
        execute(HERE/'train_bc.py',['--checkpoint',INITIAL,'--output',str(BC),'--steps','60'],'bc-training',True)
        validate_bc(INITIAL,BC)
    frozen = dict(checkpoint=str(BC),sha256=digest(BC),initial=INITIAL,initial_sha256=digest(INITIAL),
        frozen_unix=time.time(),test_results_read=False,selection='Fixed 60-step Q2 BC pilot; no test selection',
        recovery_version='human-tactics-recovery-v2')
    freeze_path = V1/'pilot-policy-freeze.json'
    if freeze_path.exists():
        previous = read(freeze_path)
        assert all(previous[key]==frozen[key] for key in ['checkpoint','sha256','initial','initial_sha256','recovery_version'])
        frozen = previous
    else:
        atomic_json(freeze_path,frozen)
    heldout = []
    for index in [6,7,14,15,22,23]:
        for role in ['attacker','defender']:
            for checkpoint,label in [(INITIAL,'baseline'),(str(BC),'bc')]:
                assert digest(BC)==frozen['sha256'] and digest(INITIAL)==frozen['initial_sha256']
                atomic_json(CONTROL,dict(state='frozen_independent_tactical_test',scenario=index,role=role,policy=label,
                    original_pipeline_unchanged=True))
                heldout.append(episode(index,role,checkpoint,label))
                aggregate = V1/'pilot-heldout-battles.json'
                if aggregate.exists():
                    prior = read(aggregate)
                    assert prior[:len(heldout)]==heldout or heldout[:len(prior)]==prior, 'Preserve incompatible heldout evidence'
                    if len(prior)>len(heldout):
                        continue
                atomic_json(aggregate,heldout)
    groups = {}
    for label,checkpoint in [('baseline',INITIAL),('bc',str(BC))]:
        rows = [row for row in heldout if row['checkpoint']==checkpoint]
        valid_losses = [row for row in rows if row['terminated'] and not row['truncated']
            and row.get('terminal_outcome') and row['terminal_outcome']['result_type']==0]
        groups[label] = dict(battles=len(rows),wins=sum(row['success'] for row in rows),
            truncations=sum(row['truncated'] for row in rows),invalid_actions=sum(row['invalid_actions'] for row in rows),
            mean_permanent_units_lost=sum(row['permanent_army_loss_units'] for row in valid_losses)/len(valid_losses) if valid_losses else None,
            permanent_loss_valid_denominator=len(valid_losses),unknown_final_losses=len(rows)-len(valid_losses),
            multi_target_opportunities=sum(row['multi_target_opportunities'] for row in rows),
            selected_multi_enemy_attacks=sum(row['selected_multi_enemy_attacks'] for row in rows))
    comparison = dict(completed=True,groups=groups,recovery_version='human-tactics-recovery-v2',quality_tier='Q2-exploratory',
        limitations='Small fixed pilot; coverage is not certified tactic success. No human traces, counter expert, historical pool or ordinary-battle regression completed.')
    destination = V1/'pilot-comparison.json'
    if destination.exists():
        assert read(destination)==comparison, 'Preserve prior comparison'
    else:
        atomic_json(destination,comparison)
    atomic_json(CONTROL,dict(state='completed_BC_pilot',original_pipeline_unchanged=True,
        full_human_curriculum_complete=False,expert_source_case_integrated=False,recovery_version='human-tactics-recovery-v2'))
    print(json.dumps(groups),flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        atomic_json(CONTROL,dict(state='failed',error=repr(error),original_pipeline_unchanged=True))
        raise
