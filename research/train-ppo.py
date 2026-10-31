import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import numpy as np
from vector_env import VectorEnv


def memory(pid):
    try:
        values = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines() if ':' in line)
        return int(values['Pss'].split()[0]) / 1024
    except FileNotFoundError:
        return 0.0


def main():
    import torch
    from decision_model import collate, load_model, save_model
    from masked_ppo import distribution, gae, update
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=12)
    parser.add_argument('--rollout', type=int, default=32)
    parser.add_argument('--updates', type=int, default=8)
    parser.add_argument('--epochs', type=int, default=3)
    parser.add_argument('--batch-size', type=int, default=64)
    parser.add_argument('--seed', type=int, default=20261014)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--inference-device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--training-device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--scenarios', default='/mnt/g/Heroes3-AI-Lab/research/scenarios-v1.json')
    parser.add_argument('--worker-python', default='/root/heroes3-ai-lab/venv/bin/python')
    parser.add_argument('--rotate-every', type=int, default=0)
    parser.add_argument('--loss-shaping', type=float, default=0.0)
    parser.add_argument('--opponents', nargs='+', default=['BattleAI'])
    parser.add_argument('--opponent-model-template', default='DATA/MMAI/models/lab-upstream-{role}.onnx')
    parser.add_argument('--cache-next-value', action='store_true')
    parser.add_argument('--fixed-map')
    parser.add_argument('--fixed-role', choices=['attacker', 'defender'])
    parser.add_argument('--checkpoint', default='/root/heroes3-ai-lab/models/bc-v1/mlp.pt')
    parser.add_argument('--validation-report', default='/mnt/g/Heroes3-AI-Lab/research/battle-evaluation-mlp.json')
    parser.add_argument('--output', default='/mnt/g/Heroes3-AI-Lab/research/ppo-short-v1.json')
    args = parser.parse_args()
    assert 0 <= args.loss_shaping <= 0.1
    tests = json.loads(Path('/mnt/g/Heroes3-AI-Lab/research/training-contract-tests.json').read_text())
    assert tests['passed'], 'Training contracts must pass'
    validation = json.loads(Path(args.validation_report).read_text())
    assert validation['checkpoint'] == args.checkpoint, 'Validation must cover the starting checkpoint'
    battles = [r for r in validation['battles'] if r['policy'] == 'model']
    assert len(battles) >= 20 and all(r['terminated'] and not r['truncated'] and r['invalid_actions'] == 0 for r in battles)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.manual_seed(args.seed)
    model, checkpoint = load_model(args.checkpoint)
    assert model.value_enabled, 'PPO needs a trainable critic'
    model.to(args.inference_device)
    model.eval()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    previous_updates = 0
    previous_steps = 0
    if args.resume:
        assert 'optimizer_state_dict' in checkpoint and 'torch_rng_state' in checkpoint
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        torch.set_rng_state(checkpoint['torch_rng_state'])
        if checkpoint.get('cuda_rng_states') and torch.cuda.is_available():
            torch.cuda.set_rng_state_all(checkpoint['cuda_rng_states'])
        previous_updates = checkpoint['completed_updates']
        prior_config = checkpoint.get('training_config', vars(args))
        previous_steps = checkpoint.get('environment_steps', previous_updates * prior_config['workers'] * prior_config['rollout'])
    from vcmi_gym.envs.v15.vcmi_env import Action
    scenarios = json.loads(Path(args.scenarios).read_text())
    training_scenarios = [s for s in scenarios if s['split'] == 'train']
    run_id = str(time.time_ns())
    configs = [dict(map=args.fixed_map or training_scenarios[i % len(training_scenarios)]['map'],
                    role=args.fixed_role or ('attacker' if (i // len(training_scenarios) + i) % 2 == 0 else 'defender'),
                    seed=args.seed + i,
                    opponent=args.opponents[i % len(args.opponents)], loss_shaping=args.loss_shaping,
                    worker_root=f'/root/heroes3-ai-lab/workers/ppo-{run_id}/{i}') for i in range(args.workers)]
    for config in configs:
        config['feature_version'] = checkpoint['feature_version']
        if config['opponent'] == 'MMAI_MODEL':
            config['opponent_model'] = args.opponent_model_template.format(role='defender' if config['role'] == 'attacker' else 'attacker')
    before_boot = time.monotonic()
    vector = VectorEnv(configs, executable=args.worker_python)
    boot_seconds = time.monotonic() - before_boot
    started = time.monotonic()
    records = []
    pids = [s['pid'] for s in vector.states]
    worker_torch_imports = [s.get('torch_imported') for s in vector.states]
    peak_pss = 0.0
    cpu_before = time.process_time()
    source_hash = hashlib.sha256(Path(args.checkpoint).read_bytes()).hexdigest()
    total_episodes = total_truncations = total_wins = 0
    action_types = Counter()
    min_available = float('inf')
    max_swap = 0.0
    checkpoint_path = f'/root/heroes3-ai-lab/models/ppo-{run_id}/latest.pt'
    try:
        for iteration in range(args.updates):
            if args.rotate_every and iteration and iteration % args.rotate_every == 0:
                vector.close()
                phase = iteration // args.rotate_every
                for i, config in enumerate(configs):
                    scenario_index = (phase * args.workers + i) % len(training_scenarios)
                    config.update(map=training_scenarios[scenario_index]['map'],
                                  role='attacker' if (phase + i) % 2 == 0 else 'defender',
                                  seed=args.seed + phase * 1000 + i,
                                  worker_root=f'/root/heroes3-ai-lab/workers/ppo-{run_id}/phase-{phase}/{i}')
                    if config['opponent'] == 'MMAI_MODEL':
                        config['opponent_model'] = args.opponent_model_template.format(role='defender' if config['role'] == 'attacker' else 'attacker')
                vector = VectorEnv(configs, executable=args.worker_python)
                pids = [s['pid'] for s in vector.states]
            model.to(args.inference_device)
            inputs, actions, logps = [], [], []
            rewards, values, next_values, terminals, truncations = [], [], [], [], []
            inference_seconds = environment_seconds = 0.0
            truncation_features = []
            rollout_started = time.monotonic()
            for step in range(args.rollout):
                current = [s['features'] for s in vector.states]
                tick = time.perf_counter()
                with torch.inference_mode():
                    batch = collate(current, args.inference_device)
                    logits, value = model(*batch)
                    dist = distribution(logits, batch[-1])
                    chosen = dist.sample()
                    logp = dist.log_prob(chosen)
                inference_seconds += time.perf_counter() - tick
                action_ids = [int(state[3][index]) for state, index in zip(current, chosen.tolist())]
                for state, index in zip(current, chosen.tolist()):
                    action_types[int(Action.decode_one(state[1][index, :7]).ACTION_TYPE)] += 1
                tick = time.perf_counter()
                transitions = vector.step(action_ids)
                environment_seconds += time.perf_counter() - tick
                if not args.cache_next_value:
                    tick = time.perf_counter()
                    with torch.inference_mode():
                        _, next_value = model(*collate([s['final_features'] if s['truncated'] and not s['terminated'] else s['features']
                                                       for s in transitions], args.inference_device))
                    inference_seconds += time.perf_counter() - tick
                    next_values.append(next_value.cpu().numpy())
                else:
                    for i, s in enumerate(transitions):
                        if s['truncated'] and not s['terminated']:
                            truncation_features.append((step, i, s['final_features']))
                inputs.extend(current)
                actions.extend(chosen.tolist())
                logps.extend(logp.tolist())
                values.append(value.cpu().numpy())
                rewards.append([s['reward'] for s in transitions])
                terminals.append([s['terminated'] for s in transitions])
                truncations.append([s['truncated'] for s in transitions])
                total_episodes += sum(s['terminated'] for s in transitions)
                total_truncations += sum(s['truncated'] and not s['terminated'] for s in transitions)
                total_wins += sum(s['terminated'] and s['reward'] > 0 for s in transitions)
                if step % 8 == 0:
                    peak_pss = max(peak_pss, sum(memory(pid) for pid in [os.getpid()] + pids))
                    mem = {k: int(v.strip().split()[0]) for k, v in (l.split(':', 1) for l in Path('/proc/meminfo').read_text().splitlines())}
                    assert mem['MemAvailable'] > 2 * 1024 * 1024, 'WSL memory reserve under 2 GiB'
                    assert mem['SwapTotal'] - mem['SwapFree'] < 256 * 1024, 'Excessive swapping'
                    min_available = min(min_available, mem['MemAvailable'] / 1024)
                    max_swap = max(max_swap, (mem['SwapTotal'] - mem['SwapFree']) / 1024)
            if args.cache_next_value:
                tick = time.perf_counter()
                with torch.inference_mode():
                    _, last_values = model(*collate([s['features'] for s in vector.states], args.inference_device))
                    next_values = np.concatenate([np.asarray(values)[1:], last_values.cpu().numpy()[None]], 0)
                    for t, i, final_features in truncation_features:
                        _, v = model(*collate([final_features], args.inference_device))
                        next_values[t, i] = float(v.item())
                inference_seconds += time.perf_counter() - tick
            rollout_seconds = time.monotonic() - rollout_started
            advantages, returns = gae(rewards, values, next_values, terminals, truncations)
            tick = time.monotonic()
            model.to(args.training_device)
            for optimizer_state in optimizer.state.values():
                for name, tensor in optimizer_state.items():
                    if torch.is_tensor(tensor) and name != 'step':
                        optimizer_state[name] = tensor.to(args.training_device)
            metrics = update(model, optimizer, inputs, actions, logps, np.asarray(values).reshape(-1),
                             advantages.reshape(-1), returns.reshape(-1), epochs=args.epochs, batch_size=args.batch_size)
            update_seconds = time.monotonic() - tick
            save_model(model, checkpoint_path, source='BC initialized masked PPO; pure terminal win/loss reward',
                       seed=args.seed, completed_updates=previous_updates+iteration+1, optimizer_state_dict=optimizer.state_dict(),
                       environment_steps=previous_steps + (iteration+1) * args.workers * args.rollout,
                       torch_rng_state=torch.get_rng_state(), source_checkpoint_sha256=source_hash,
                       cuda_rng_states=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
                       training_config=vars(args))
            if (iteration + 1) % 16 == 0:
                save_model(model, str(Path(checkpoint_path).with_name(f'update-{previous_updates+iteration+1}.pt')),
                           source='Periodic PPO policy snapshot', seed=args.seed,
                           completed_updates=previous_updates+iteration+1)
            record = dict(update=iteration+1, steps=len(inputs), rollout_seconds=rollout_seconds,
                          actions_sha256=hashlib.sha256(np.asarray(actions, dtype=np.int64).tobytes()).hexdigest(),
                          returns_sha256=hashlib.sha256(np.asarray(returns, dtype=np.float32).tobytes()).hexdigest(),
                          inference_seconds=inference_seconds, environment_ipc_seconds=environment_seconds,
                          update_seconds=update_seconds,
                          effective_steps_per_second=len(inputs)/(rollout_seconds+update_seconds),
                          episodes_total=total_episodes, wins_total=total_wins, truncations_total=total_truncations,
                          sampled_peak_total_pss_mib=peak_pss, metrics=metrics)
            record['action_types_total'] = dict(action_types)
            record['wsl_min_available_mib'] = min_available
            record['wsl_max_swap_used_mib'] = max_swap
            if args.training_device == 'cuda' and iteration % 16 == 0:
                gpu_values = subprocess.check_output(['nvidia-smi', '--query-gpu=temperature.gpu,memory.used,utilization.gpu',
                                                       '--format=csv,noheader,nounits'], text=True).strip().splitlines()[0].split(',')
                record['gpu_telemetry'] = dict(zip(['temperature_c', 'memory_used_mib', 'utilization_percent'],
                                                   [float(v.strip()) for v in gpu_values]))
                assert record['gpu_telemetry']['temperature_c'] < 86, 'GPU temperature exceeded experiment limit'
                assert record['gpu_telemetry']['memory_used_mib'] < 14000, 'GPU memory reserve too low'
            assert total_truncations <= max(2, total_episodes * 0.05), 'Too many truncated battles'
            records.append(record)
            result = dict(run_id=run_id, config=vars(args), checkpoint=checkpoint_path,
                          source_checkpoint_sha256=source_hash, boot_seconds=boot_seconds,
                          resumed_from_updates=previous_updates,
                          worker_torch_imported=worker_torch_imports,
                          wall_seconds=time.monotonic()-started,
                          parent_cpu_seconds=time.process_time()-cpu_before, sampled_peak_total_pss_mib=peak_pss,
                          torch_version=torch.__version__,
                          gpu_peak_allocated_mib=torch.cuda.max_memory_allocated()/1024**2 if torch.cuda.is_available() else None,
                          reward=f'0 except +1/-1 at authoritative normal battle termination, optional terminal casualty-rate shaping weight {args.loss_shaping}; truncation bootstraps final state',
                          records=records, completed=False)
            Path(args.output).write_text(json.dumps(result, indent=2))
            print(json.dumps(record), flush=True)
        vector.close()
        result.update(completed=True, all_workers_exit_zero=True,
                      checkpoint_sha256=hashlib.sha256(Path(checkpoint_path).read_bytes()).hexdigest())
        Path(args.output).write_text(json.dumps(result, indent=2))
        print('PPO SHORT RUN COMPLETE', checkpoint_path, flush=True)
    except BaseException:
        vector.abort()
        raise


if __name__ == '__main__':
    main()
