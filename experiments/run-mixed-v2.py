"""Corrected orchestrator: re-execute the frozen B64-anchored mixed PPO pilot.

Differences from the abandoned run-next-mixed.py:
  * new plan filename (b64-anchor-plan-v2.json) and new output directory
  * no stale prerequisite PIDs; prerequisites are already completed and archived
  * never treats the 7 logged updates of attempt v1 as a resumable checkpoint
  * refuses to start if any mixed trainer / evaluator is already live
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent / 'research'
sys.path.insert(0, str(RESEARCH))
from lab_io import atomic_json
from evaluation_provenance import digest

MIXED = HERE / 'expert-mixed-ppo-v1'
PLAN = MIXED / 'b64-anchor-plan-v2.json'
TRAIN_JSON = MIXED / 'b64-anchor-plan-v2' / 'training.json'
OUT = HERE / 'expert-mixed-b64-run-v2'
STATUS = OUT / 'control.json'
B64 = '/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt'
B64_SHA = '1e022707186a3c0dad7c671233b100930e870fff6c79cc703fb5b89dfb192936'
ATTEMPT_V1_LAST_UPDATE = 7  # logged only, no weights/optimizer were saved


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def run(command, name, gpu=False):
    with (OUT / (name + '.log')).open('ab') as log:
        subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT,
                       env=dict(os.environ,
                                LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python' if gpu
                                else '/root/heroes3-ai-lab/venv/bin/python'))


def live_trainers():
    hits = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / 'cmdline').read_bytes().decode('utf-8', 'replace')
        except OSError:
            continue
        if any(token in cmdline for token in ('train_mixed_heads.py', 'run_experiment.py --run',
                                              'evaluate-battles.py')):
            hits.append((int(entry.name), cmdline.replace('\x00', ' ').strip()))
    return hits


def verify_evaluation(path, checkpoint, opponent):
    data = read(path)
    assert data['checkpoint'] == checkpoint and data['opponent'] == opponent
    assert data['scenario_file'] == str(RESEARCH / 'diverse-curriculum.json')
    assert data['scenario_ids'] == list(range(192, 240)) and data['workers'] == 12
    assert data['opponent_model_template'] == (
        'DATA/MMAI/models/lab-upstream-{role}.onnx' if opponent == 'MMAI_MODEL' else None)
    assert data['artifacts_checked_before_and_after'] and data['frozen_artifacts'][checkpoint] == digest(checkpoint)
    rows = data['battles']
    assert len(rows) == 192
    expected = {(f'diverse-{index:03d}', role, 2026101400 + index * 100 + seed)
                for index in range(192, 240) for role in ['attacker', 'defender'] for seed in range(2)}
    assert {(row['scenario'], row['role'], row['seed']) for row in rows} == expected
    from battle_outcome_audit import audit
    audit(rows)
    summary = data['summary'][0]
    assert summary['battles'] == 192 and summary['wins'] == sum(row['success'] for row in rows)
    # Illegal actions and non-normal endings invalidate a cell; truncations are recorded, never counted as wins.
    assert summary['invalid_actions'] == summary['non_normal_terminations'] == 0
    if summary['truncated']:
        summary['truncation_flag'] = 'non-zero truncations; excluded from wins, reported explicitly'
    return summary


def preflight(plan):
    assert plan['finalized_for_execution']
    assert plan['initial_checkpoint'] == plan['reference_checkpoint'] == B64
    assert plan['initial_sha256'] == plan['reference_sha256'] == B64_SHA
    assert digest(B64) == B64_SHA, 'B64 initial weights changed on disk'
    assert plan['learning_rate'] == 1e-4 and plan['updates'] == 32 and plan['workers'] == 24
    check = read(MIXED / 'cpu-preflight.json')
    assert check['passed'] and check['plan_sha256'] == digest(PLAN), 'CPU preflight does not match this plan'
    assert check['CUDA_started'] is False and check['simulator_started'] is False
    busy = live_trainers()
    assert not busy, 'Refusing to start, another trainer/evaluator is live: ' + repr(busy)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--train-only', action='store_true')
    parser.add_argument('--eval-only', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    plan = read(PLAN)
    preflight(plan)
    manifest = dict(plan=str(PLAN), plan_sha256=digest(PLAN), controller_sha256=digest(__file__),
                    attempt='v2', supersedes_partial_attempt='expert-mixed-ppo-v1/b64-anchor-plan',
                    attempt_v1_last_logged_update=ATTEMPT_V1_LAST_UPDATE,
                    attempt_v1_resumable_checkpoint=False,
                    evaluation_script_sha256=digest(RESEARCH / 'evaluate-battles.py'),
                    development_scenarios=list(range(192, 240)), roles=2, seeds=2,
                    opponents=['BattleAI', 'MMAI_MODEL'],
                    candidates=['b64-baseline', 'mixed-16', 'mixed-32'],
                    games_per_matchup=192, total_development_games=1152,
                    independent_confirmation=False, new_confirmation_results_used=False)
    manifest_path = OUT / 'orchestration-plan.json'
    if manifest_path.exists():
        assert read(manifest_path) == manifest, 'Orchestration manifest changed; inspect before overwriting'
    else:
        atomic_json(manifest_path, manifest)

    if not args.eval_only:
        if TRAIN_JSON.exists() and read(TRAIN_JSON).get('completed'):
            print('training already completed for this plan; skipping', flush=True)
        else:
            atomic_json(STATUS, dict(state='launching_mixed_training', workers=24, updates=32,
                                     start_checkpoint=B64, start_sha256=B64_SHA))
            run(['bash', str(RESEARCH / 'run-lab.sh'), str(MIXED / 'run_experiment.py'),
                 '--run', '--plan', str(PLAN)], 'mixed-training')
        training = read(TRAIN_JSON)
        assert training['completed'] and training['CUDA_training'] and training['all_workers_exit_zero']
        assert training['plan_sha256'] == manifest['plan_sha256']
        assert digest(training['checkpoint']) == training['checkpoint_sha256']
        assert training['resumed_from_update'] == 0, 'Must start from B64, not from the v1 partial updates'
        atomic_json(STATUS, dict(state='training_complete', latest_update=training['latest_update'],
                                 checkpoint=training['checkpoint'],
                                 checkpoint_sha256=training['checkpoint_sha256']))

    if args.train_only:
        return

    training = read(TRAIN_JSON)
    candidates = [('b64-baseline', plan['initial_checkpoint']),
                  ('mixed-16', str(Path(training['checkpoint']).with_name('update-16.pt'))),
                  ('mixed-32', training['checkpoint'])]
    results = []
    for name, checkpoint in candidates:
        row = dict(name=name, checkpoint=checkpoint, checkpoint_sha256=digest(checkpoint))
        for opponent in manifest['opponents']:
            output = OUT / f'{name}-{opponent}-development.json'
            atomic_json(STATUS, dict(state='expanded_development_validation', candidate=name, opponent=opponent))
            if not output.exists():
                assert digest(RESEARCH / 'evaluate-battles.py') == manifest['evaluation_script_sha256']
                command = ['/root/heroes3-ai-lab/venv/bin/python', str(RESEARCH / 'evaluate-battles.py'),
                           '--checkpoint', checkpoint, '--policies', 'recovered',
                           '--scenario-file', str(RESEARCH / 'diverse-curriculum.json'),
                           '--scenarios', *map(str, range(192, 240)), '--seeds', '2',
                           '--workers', '12', '--opponent', opponent, '--output', str(output)]
                if opponent == 'MMAI_MODEL':
                    command += ['--opponent-model-template', 'DATA/MMAI/models/lab-upstream-{role}.onnx']
                run(command, output.stem)
            row[opponent] = dict(summary=verify_evaluation(output, checkpoint, opponent),
                                 report=str(output), sha256=digest(output))
        results.append(row)
        atomic_json(OUT / 'development-results.json', dict(complete=False, results=results, goal_achieved=False))
    atomic_json(OUT / 'development-results.json',
                dict(complete=True, results=results, goal_achieved=False, independent_confirmation=False))
    atomic_json(STATUS, dict(state='mixed_development_complete', goal_achieved=False,
                             new_confirmation_required=True))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        OUT.mkdir(exist_ok=True)
        atomic_json(STATUS, dict(state='repair_needed', error=repr(error), goal_achieved=False))
        raise
