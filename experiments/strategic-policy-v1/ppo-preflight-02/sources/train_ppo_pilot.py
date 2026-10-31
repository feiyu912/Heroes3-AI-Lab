#!/usr/bin/env python3
"""Exploratory full-game strategic PPO; CUDA policy, native CPU simulation.

Only completed native games supply terminal +/-1 returns. No trained-policy
win claim is made from these curriculum games. Existing battle models untouched.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import signal
import subprocess
import sys
import tempfile
import time

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
import torch
from torch.distributions import Categorical
from encoder import collate, validate, ENCODER_VERSION
from model import load_checkpoint, PRIOR_FORMAT

HERE = Path(__file__).resolve().parent
RUNNER = HERE.parent / 'adventure_runner_v5.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False))
    os.replace(tmp, path)


def save_model(model, optimizer, path, update, plan_sha, protocol_sha):
    data = dict(format=PRIOR_FORMAT, encoder_version=ENCODER_VERSION, hidden=model.hidden,
                prior_config=dict(prior_scale=float(model.prior_scale.detach().cpu()),
                                  prior_feature_index=model.prior_feature_index),
                state_dict={k: v.detach().cpu() for k, v in model.state_dict().items()},
                trained=update > 0, training_updates=update, optimizer=optimizer.state_dict(),
                torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all(),
                python_rng=random.getstate(), plan_sha256=plan_sha, protocol_sha256=protocol_sha,
                value_is_win_probability=False, scope='Target choice only; economics and battles delegated.')
    torch.save(data, path)


def collect(model, job, output, device):
    output.mkdir()
    directory = Path(tempfile.mkdtemp(prefix=output.name + '-',
        dir='/root/heroes3-ai-lab/workers/strategy-agent-runs'))
    command = [sys.executable, str(RUNNER), '--map', job['map'], '--red', job['red'],
               '--blue', job['blue'], '--seed', str(job['seed']), '--seconds', '90',
               '--agent-dir', str(directory), '--tag', output.name]
    samples = []
    started = time.monotonic()
    with (output / 'runner.log').open('w') as log, (directory / 'rollout.jsonl').open('w') as trace:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            number = 1
            while proc.poll() is None:
                path = directory / f'request-{number:08d}.json'
                if not path.exists():
                    time.sleep(.001)
                    continue
                request = validate(json.loads(path.read_text()), number)
                with torch.no_grad():
                    logits, values = model(**collate([request], device))
                    assert torch.isfinite(logits[logits != -torch.inf]).all() and torch.isfinite(values).all()
                    distribution = Categorical(logits=logits[0])
                    action = distribution.sample()
                    logprob = float(distribution.log_prob(action))
                    value = float(values[0])
                selected = int(action)
                if not 0 <= selected < len(request['candidates']):
                    raise RuntimeError('Policy action outside legal candidate mask')
                row = dict(request=request, action=selected, old_logprob=logprob, old_value=value,
                           request_sha256=sha(path), model_device=str(device))
                samples.append(row)
                trace.write(json.dumps(row, allow_nan=False) + '\n')
                trace.flush()
                response = directory / f'action-{number:08d}.json'
                tmp = response.with_suffix('.tmp')
                tmp.write_text(str(selected) + '\n')
                os.replace(tmp, response)
                number += 1
            code = proc.wait()
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
    log = (output / 'runner.log').read_text()
    results = [json.loads(line) for line in log.splitlines() if line.startswith('{')]
    result = results[-1] if results else dict(completed=False, error='Native result missing')
    native_choices = []
    if result.get('run_dir'):
        decisions = Path(result['run_dir']) / 'strategy-decisions.jsonl'
        if decisions.exists():
            native_choices = [json.loads(line) for line in decisions.read_text().splitlines()]
    consumed = len(native_choices) == len(samples) and bool(samples)
    if consumed:
        for sample, native in zip(samples, native_choices):
            request = sample['request']
            candidate = request['candidates'][sample['action']]
            consumed = consumed and native['selected_candidate'] == sample['action'] and all(
                native[k] == request[k] for k in ['player', 'day', 'hero', 'from']) and (
                    native['destination'] == candidate['position'] and native['step'] == candidate['next'])
    our_color = 'red' if job['red'] == 'DirectorAI' else 'blue'
    valid = code == 0 and result.get('completed') and consumed
    reward = (1.0 if result.get('winner') == our_color else -1.0) if valid else None
    for row in samples:
        row['return'] = reward
    record = dict(config=job, valid=bool(valid), reward=reward, decisions=len(samples),
                  native_consumption_verified=bool(consumed),
                  native=result, rollout_dir=str(directory), wall_seconds=time.monotonic() - started)
    atomic_json(output / 'episode.json', record)
    return samples, record


def ppo_update(model, optimizer, samples, device):
    old_logprob = torch.tensor([s['old_logprob'] for s in samples], device=device)
    returns = torch.tensor([s['return'] for s in samples], device=device)
    advantages = returns - torch.tensor([s['old_value'] for s in samples], device=device)
    advantages = (advantages - advantages.mean()) / advantages.std(unbiased=False).clamp_min(1e-6)
    metrics = []
    for epoch in range(4):
        for indices in torch.randperm(len(samples)).split(64):
            batch = indices.tolist()
            target = torch.tensor(batch, device=device)
            encoded = collate([samples[i]['request'] for i in batch], device)
            actions = torch.tensor([samples[i]['action'] for i in batch], device=device)
            logits, values = model(**encoded)
            distribution = Categorical(logits=logits)
            new_logprob = distribution.log_prob(actions)
            ratio = (new_logprob - old_logprob[target]).exp()
            actor = -torch.minimum(ratio * advantages[target],
                                   ratio.clamp(.8, 1.2) * advantages[target]).mean()
            critic = .5 * (values - returns[target]).square().mean()
            entropy = distribution.entropy().mean()
            loss = actor + .5 * critic - .005 * entropy
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            if not all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters()):
                raise RuntimeError('Nonfinite gradient')
            torch.nn.utils.clip_grad_norm_(model.parameters(), .5)
            optimizer.step()
            approx_kl = float(((ratio - 1) - (new_logprob - old_logprob[target])).mean().detach())
            metrics.append(dict(loss=float(loss.detach()), actor=float(actor.detach()),
                                critic=float(critic.detach()), entropy=float(entropy.detach()), kl=approx_kl))
            if approx_kl > .05:
                return dict(minibatches=len(metrics), early_stop_kl=True, last=metrics[-1])
    return dict(minibatches=len(metrics), early_stop_kl=False, last=metrics[-1])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--updates', type=int, default=4)
    p.add_argument('--preflight', action='store_true')
    p.add_argument('--resume', type=Path, help='Same-protocol complete-update checkpoint; target --updates remains total')
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    torch.manual_seed(2026101827)
    random.seed(2026101827)
    torch.use_deterministic_algorithms(True)
    initial = HERE / 'checkpoints/prior-initial-v2.pt'
    sources = [Path(__file__), HERE / 'encoder.py', HERE / 'model.py', RUNNER]
    sources += [Path('/root/heroes3-ai-lab/src/vcmi-adv-build/bin') / n
                for n in ['vcmiclient', 'vcmiserver', 'libvcmi.so']]
    map_inputs = [Path('/root/heroes3-ai-lab/data/vcmi/Maps/adv') / (name + '.vmap')
                  for name in ['takeover-v2-train-01-mines', 'takeover-v2-train-02-development']]
    hashes = {str(f): sha(f) for f in sources + [initial] + map_inputs}
    jobs = []
    for update in range(1, args.updates + 1):
        group = []
        for i, opponent in enumerate(['EmptyAI', 'EmptyAI', 'Nullkiller2', 'Nullkiller2']):
            ours = i % 2 == 0
            group.append(dict(map='Maps/adv/takeover-v2-' +
                              ('train-01-mines' if update % 2 else 'train-02-development'),
                              red='DirectorAI' if ours else opponent,
                              blue=opponent if ours else 'DirectorAI',
                              seed=2026101900 + update * 10 + i))
        jobs.append(group)
    plan = dict(schema='strategic-ppo-pilot-v1', updates=args.updates, jobs=jobs,
                initial_sha256=sha(initial), hashes=hashes, lr=0.0003, clip=.2, gamma=1.0,
                entropy=.005, episodes_per_update=4, simultaneous_environments=1,
                reward='Native terminal win +1/loss -1. No shaping. Invalid episodes abort pilot.',
                evaluation='Training curriculum only; dev/test not touched. No promotion from training wins.')
    atomic_json(args.out / 'plan.json', plan)
    protocol = {k: v for k, v in plan.items() if k not in ['updates', 'jobs']}
    protocol['job_schedule'] = 'v2: map alternates by update; each opponent gets both roles every update; seed=2026101900+10*update+i'
    protocol_sha = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    atomic_json(args.out / 'protocol.json', dict(protocol=protocol, sha256=protocol_sha))
    snapshot = args.out / 'sources'
    snapshot.mkdir()
    import shutil
    for path in sources:
        if path.suffix == '.py':
            shutil.copy2(path, snapshot / path.name)
    device = torch.device('cpu' if args.preflight else 'cuda')
    if not args.preflight and not torch.cuda.is_available():
        raise RuntimeError('CUDA required; no silent CPU fallback')
    model = load_checkpoint(args.resume or initial, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=.0003)
    start_update = 0
    if args.resume:
        bundle = torch.load(args.resume, map_location='cpu', weights_only=True)
        if bundle.get('protocol_sha256') != protocol_sha:
            raise ValueError('Resume protocol differs; do not silently reuse an optimizer under a new recipe')
        start_update = int(bundle['training_updates'])
        if not 0 <= start_update < args.updates:
            raise ValueError('Resume requires a checkpoint before target total updates')
        optimizer.load_state_dict(bundle['optimizer'])
        torch.set_rng_state(bundle['torch_rng'].cpu())
        torch.cuda.set_rng_state_all([s.cpu() for s in bundle['cuda_rng']])
        random.setstate(bundle['python_rng'])
    if args.preflight:
        reference = Path('/root/heroes3-ai-lab/workers/strategy-agent-runs/strategic-prior-smoke-v2-apackbnp/request-00000001.json')
        request = json.loads(reference.read_text())
        logits, values = model(**collate([request], device))
        loss = -Categorical(logits=logits).log_prob(logits.argmax(dim=-1)).mean() + values.square().mean()
        loss.backward()
        nonzero = sum(p.grad is not None and bool(p.grad.abs().sum() > 0) for p in model.parameters())
        assert nonzero > 0 and all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())
        atomic_json(args.out / 'preflight.json', dict(passed=True, device=str(device), nonzero_gradients=nonzero,
                    game_started=False, cuda_training_started=False))
        print('CPU_PREFLIGHT_PASSED')
        return 0
    lock = Path('/root/heroes3-ai-lab/evaluations/.gpu-learner-lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    report = dict(status='running', CUDA_training=False, CUDA_inference=True, device=torch.cuda.get_device_name(),
                  torch_version=torch.__version__, updates=[], episodes=[], independent_evaluation=False,
                  resumed_from_update=start_update, resume_checkpoint=str(args.resume) if args.resume else None,
                  decision_weighting='Uniform transitions in minibatches; per-episode lengths reported, never treated as independent games.')
    initial_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    try:
        save_model(model, optimizer, args.out / f'update-{start_update}.pt', start_update, sha(args.out / 'plan.json'), protocol_sha)
        for update, group in list(enumerate(jobs, 1))[start_update:]:
            assert all(sha(Path(f)) == h for f, h in hashes.items()), 'Frozen source/runtime changed'
            samples = []
            for i, job in enumerate(group):
                rows, episode = collect(model, job, args.out / f'update-{update}-episode-{i}', device)
                assert all(sha(Path(f)) == h for f, h in hashes.items()), 'Code/runtime changed during collection'
                report['episodes'].append(episode)
                atomic_json(args.out / 'training.json', report)
                if not episode['valid']:
                    raise RuntimeError('Invalid native episode; no result or samples accepted for PPO')
                samples.extend(rows)
                print(json.dumps(dict(update=update, episode=i, reward=episode['reward'], steps=len(rows))), flush=True)
            metrics = ppo_update(model, optimizer, samples, device)
            report['CUDA_training'] = True
            assert all(sha(Path(f)) == h for f, h in hashes.items()), 'Code/runtime changed during optimizer update'
            changed = sum(not torch.equal(v, initial_state[k]) for k, v in model.state_dict().items())
            checkpoint = args.out / f'update-{update}.pt'
            save_model(model, optimizer, checkpoint, update, sha(args.out / 'plan.json'), protocol_sha)
            report['updates'].append(dict(update=update, samples=len(samples), changed_tensors=changed,
                                          checkpoint=str(checkpoint), sha256=sha(checkpoint), metrics=metrics))
            atomic_json(args.out / 'training.json', report)
            print(json.dumps(dict(update=update, changed_tensors=changed, metrics=metrics)), flush=True)
        report['status'] = 'completed'
        report['peak_cuda_memory_bytes'] = torch.cuda.max_memory_allocated()
        return 0
    except BaseException as error:
        report['status'] = 'failed'
        report['error'] = repr(error)
        raise
    finally:
        atomic_json(args.out / 'training.json', report)
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


if __name__ == '__main__':
    raise SystemExit(main())
