"""One real 24-worker CUDA continuation, excluded from strength selection.

Run after the final scheduled graph experiment exits. Share the evaluation pool
lock so the probe cannot add 24 simulators on top of a 12-worker evaluation.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from lab_io import atomic_json


def learners():
    found = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            args = (entry / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if len(args) > 1 and Path(os.fsdecode(args[1])).name in ['train-graph-finetune.py', 'train-recovered-heads.py']:
            found.append(int(entry.name))
    return found


def main():
    research = Path(__file__).resolve().parent
    status = research / 'live-training-resume-contract.json'
    source_report = research / 'v5-diverse-all.json'
    atomic_json(status, dict(state='waiting_for_final_training_exit', probe_excluded_from_selection=True))
    while True:
        if source_report.exists():
            data = json.loads(source_report.read_text())
            if data.get('completed') and not learners():
                break
        control = json.loads((research / 'goal-v5-control.json').read_text())
        assert control['state'] != 'failed', 'Scheduled training failed; do not launch probe'
        time.sleep(10)
    with Path('/root/heroes3-ai-lab/evaluations/.pool-lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert not learners(), 'Another CUDA learner started; preserve one-trainer invariant'
        source = Path(data['checkpoint'])
        checksum = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        source_hash = checksum(source)
        config = data['config']
        output = research / 'v5-live-resume-probe.json'
        command = ['bash', str(research / 'run-lab.sh'), str(research / 'train-graph-finetune.py'),
                   '--checkpoint', str(source), '--resume', '--updates', '1', '--output', str(output)]
        for key in ['mode', 'workers', 'rollout', 'microbatch', 'epochs', 'seed', 'learning_rate',
                    'head_learning_rate', 'scenario_file', 'shaping', 'step_cost', 'rotate_every',
                    'native_opponent_device']:
            command += ['--' + key.replace('_', '-'), str(config[key])]
        command += ['--opponents', *config['opponents'], '--no-auto-microbatch']
        for key in ['gamma', 'gae_lambda', 'entropy_coef']:
            if key in config:
                command += ['--' + key.replace('_', '-'), str(config[key])]
        if config.get('first_battle'):
            command += ['--first-battle']
        atomic_json(status, dict(state='running', source_checkpoint=str(source), sha256=source_hash,
                                workers=24, probe_excluded_from_selection=True))
        with (research / 'v5-live-resume-probe.log').open('wb') as log:
            subprocess.run(command, check=True, timeout=1800, stdout=log, stderr=subprocess.STDOUT,
                           env=dict(os.environ, LAB_PYTHON='/root/heroes3-ai-lab/gpu-venv/bin/python', LAB_STAGED_BOOT='1'))
        result = json.loads(output.read_text())
        assert result['completed'] and result['all_workers_exit_zero'] and result['CUDA_training']
        assert result['config']['workers'] == 24 and len(result['records']) == 1
        import torch
        torch.set_num_threads(1)
        before = torch.load(source, map_location='cpu', weights_only=True)
        after = torch.load(result['checkpoint'], map_location='cpu', weights_only=True)
        assert checksum(source) == source_hash
        assert result['resumed_from_updates'] == before['completed_updates']
        assert after['completed_updates'] == before['completed_updates'] + 1
        assert after['environment_steps'] == before['environment_steps'] + 24 * config['rollout']
        old_optimizer = before['optimizer_state_dict']['state']
        new_optimizer = after['optimizer_state_dict']['state']
        assert set(old_optimizer) == set(new_optimizer)
        increments = [float(new_optimizer[key]['step'] - old_optimizer[key]['step']) for key in old_optimizer]
        assert min(increments) >= 0 and max(increments) > 0
        assert any(not torch.equal(before['models'][role]['weights'][name], value)
                   for role in after['models'] for name, value in after['models'][role]['weights'].items())
        assert all(torch.isfinite(value).all() for role in after['models']
                   for value in after['models'][role]['weights'].values())
        assert not torch.equal(before['torch_rng_state'], after['torch_rng_state']) or any(
            not torch.equal(a, b) for a, b in zip(before['cuda_rng_states'], after['cuda_rng_states']))
        atomic_json(status, dict(state='completed', passed=True, source_checkpoint=str(source),
            source_sha256=source_hash, resumed_checkpoint=result['checkpoint'],
            resumed_sha256=checksum(result['checkpoint']), workers=24, CUDA_training=True,
            optimizer_steps_increment_range=[min(increments), max(increments)],
            environment_steps_increment=24 * config['rollout'], all_workers_exit_zero=True,
            truncated_transitions=result['records'][0]['truncations'],
            probe_excluded_from_selection=True, no_concurrent_evaluation_or_learner=True,
            scope='Optimizer/RNG continuation correctness, not playing strength. Legitimate time-cap truncations use the already checked bootstrap path and are recorded separately.'))
        print('Real CUDA checkpoint/optimizer/RNG continuation passed', flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        atomic_json(Path(__file__).with_name('live-training-resume-contract.json'),
                    dict(state='failed', passed=False, error=repr(error), probe_excluded_from_selection=True))
        raise
