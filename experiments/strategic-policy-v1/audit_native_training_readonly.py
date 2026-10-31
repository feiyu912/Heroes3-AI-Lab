#!/usr/bin/env python3
"""Post-run CPU audit: no games, CUDA contexts or optimizer steps."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

import torch
from torch.distributions import Categorical

from encoder import collate
from model import load_checkpoint
from verify_training_boundary import compare, assert_frozen, atomic_json, sha


def delta(before, after):
    result = {}
    for group in ('actor', 'critic'):
        differences = [(after[name].double() - value.double()) for name, value in before.items()
                       if name.startswith(group + '.')]
        result[group] = dict(changed_tensors=sum(bool(value.ne(0).any()) for value in differences),
            total_tensors=len(differences), l2_delta=sum(float(value.square().sum()) for value in differences) ** .5,
            max_abs_delta=max(float(value.abs().max()) for value in differences))
    return result


def actor_gradient_probe(model, rows, advantages, singleton):
    model.zero_grad(set_to_none=True)
    selected = [index for index, row in enumerate(rows) if (len(row['request']['candidates']) == 1) == singleton]
    if not selected:
        return dict(samples=0, actor_gradient_l2=None)
    for offset in range(0, len(selected), 64):
        batch = selected[offset:offset + 64]
        logits, _ = model(**collate([rows[index]['request'] for index in batch]))
        distribution = Categorical(logits=logits)
        logprob = distribution.log_prob(torch.tensor([rows[index]['action'] for index in batch]))
        old = torch.tensor([rows[index]['old_logprob'] for index in batch])
        ratio = (logprob - old).exp()
        # Initial-update actor+entropy gradient on the archived data. This is a
        # CPU diagnostic backward, never an optimizer update or native action.
        objective = -(ratio * advantages[batch]).sum() / len(rows) - .005 * distribution.entropy().sum() / len(rows)
        objective.backward()
    gradients = [parameter.grad for name, parameter in model.named_parameters() if name.startswith('actor.')]
    return dict(samples=len(selected), actor_gradient_l2=sum(float(gradient.double().square().sum())
                for gradient in gradients if gradient is not None) ** .5,
                all_finite=all(gradient is None or bool(torch.isfinite(gradient).all()) for gradient in gradients))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    root = args.root.resolve()
    plan = json.loads((root / 'plan.json').read_text())
    assert_frozen(plan['hashes'])
    boundary = compare(root)
    assert boundary['passed'], 'Native boundary comparison failed; inspect original evidence'
    stages = {}
    for name in ('continuous-2', 'split-1', 'resume-2'):
        report = json.loads((root / name / 'training.json').read_text())
        files = sorted((root / name).glob('update-*.pt'))
        counts = []
        for path in files:
            bundle = torch.load(path, map_location='cpu', weights_only=True)
            step_values = [int(state['step']) for state in bundle['optimizer']['state'].values()]
            observed = max(step_values, default=0)
            assert observed == bundle['optimizer_steps_total']
            counts.append(dict(path=str(path), sha256=sha(path), complete_update=bundle['training_updates'],
                               Adam_steps_per_parameter=dict(Counter(step_values)), observed_total_steps=observed))
        observed_run = counts[-1]['observed_total_steps'] - counts[0]['observed_total_steps']
        assert observed_run == report['optimizer_steps_this_run']
        assert report['CUDA_training'] == (observed_run > 0)
        stages[name] = dict(status=report['status'], CUDA_training=report['CUDA_training'],
            optimizer_steps_this_run=observed_run, optimizer_steps_total=report['optimizer_steps_total'],
            checkpoints=counts, lineage=report['lineage'])
    report = json.loads((root / 'continuous-2/training.json').read_text())
    updates = []
    for update in report['updates']:
        number = update['update']
        before_path, after_path = root / f'continuous-2/update-{number-1}.pt', root / f'continuous-2/update-{number}.pt'
        before = torch.load(before_path, map_location='cpu', weights_only=True)
        after = torch.load(after_path, map_location='cpu', weights_only=True)
        actual_delta = delta(before['state_dict'], after['state_dict'])
        assert actual_delta == update['parameter_delta_from_previous_update']
        steps = after['optimizer_steps_total'] - before['optimizer_steps_total']
        assert steps == update['metrics']['optimizer_steps']
        rows, episodes, native_statuses = [], [], Counter()
        for episode_index in range(4):
            episode = json.loads((root / f'continuous-2/update-{number}-episode-{episode_index}/episode.json').read_text())
            episode_rows = [json.loads(line) for line in (Path(episode['rollout_dir']) / 'rollout.jsonl').read_text().splitlines()]
            for row in episode_rows:
                row['return'] = episode['reward']
            rows.extend(episode_rows)
            chosen = Counter(str(row['request']['candidates'][row['action']]['kind']) for row in episode_rows)
            native = episode['native']
            native_dir = Path(native['run_dir'])
            target_trace = native_dir / 'strategy-trace.jsonl.targets.jsonl'
            if target_trace.exists():
                native_statuses.update(json.loads(line).get('status', '<missing>') for line in target_trace.read_text().splitlines())
            log = (native_dir / 'client.log').read_text(errors='replace')
            episodes.append(dict(config=episode['config'], reward=episode['reward'], valid=episode['valid'],
                decisions=len(episode_rows), max_decision_day=max(row['request']['day'] for row in episode_rows),
                singleton_decisions=sum(len(row['request']['candidates']) == 1 for row in episode_rows),
                selected_kinds=dict(chosen), native_moves=native.get('moves_requested'),
                native_changed_tile_replies=native.get('changed_tile_replies'),
                visibility_warning_count=log.count('That hero is not visible!'),
                no_target_count=log.count('no target for hero'), external_policy_failure_count=log.count('external policy failed')))
        assert len(rows) == update['samples']
        model_before, model_after = load_checkpoint(before_path), load_checkpoint(after_path)
        counts = Counter(len(row['request']['candidates']) for row in rows)
        stats = dict(max_old_logprob_error=0., max_old_value_error=0., singleton_max_abs_logprob=0.,
                     singleton_max_entropy=0., greedy_action_changes=0, mean_behavior_KL=0.,
                     probability_total_variation_mean=0., multi_candidate_entropy_sum=0.)
        for offset in range(0, len(rows), 64):
            batch = rows[offset:offset + 64]
            encoded = collate([row['request'] for row in batch])
            with torch.no_grad():
                old_logits, old_values = model_before(**encoded)
                new_logits, _ = model_after(**encoded)
                old_dist, new_dist = Categorical(logits=old_logits), Categorical(logits=new_logits)
                selected_logprob = old_dist.log_prob(torch.tensor([row['action'] for row in batch]))
                stats['max_old_logprob_error'] = max(stats['max_old_logprob_error'], float((selected_logprob -
                    torch.tensor([row['old_logprob'] for row in batch])).abs().max()))
                stats['max_old_value_error'] = max(stats['max_old_value_error'], float((old_values -
                    torch.tensor([row['old_value'] for row in batch])).abs().max()))
                stats['greedy_action_changes'] += int((old_logits.argmax(-1) != new_logits.argmax(-1)).sum())
                finite_difference = torch.where(encoded['mask'], old_dist.logits - new_dist.logits, 0.)
                stats['mean_behavior_KL'] += float((old_dist.probs * finite_difference).sum()) / len(rows)
                stats['probability_total_variation_mean'] += float((old_dist.probs - new_dist.probs).abs().sum()) / (2 * len(rows))
                entropies = old_dist.entropy()
                for index, row in enumerate(batch):
                    if len(row['request']['candidates']) == 1:
                        stats['singleton_max_abs_logprob'] = max(stats['singleton_max_abs_logprob'], abs(float(selected_logprob[index])))
                        stats['singleton_max_entropy'] = max(stats['singleton_max_entropy'], float(entropies[index]))
                    else:
                        stats['multi_candidate_entropy_sum'] += float(entropies[index])
        multi_count = sum(number * count for number, count in [(1, amount) for width, amount in counts.items() if width > 1])
        stats['multi_candidate_entropy_mean'] = stats.pop('multi_candidate_entropy_sum') / max(multi_count, 1)
        advantages = torch.tensor([row['return'] - row['old_value'] for row in rows])
        advantages = (advantages - advantages.mean()) / advantages.std(unbiased=False).clamp_min(1e-6)
        probes = dict(singleton=actor_gradient_probe(model_before, rows, advantages, True),
                      multi_candidate=actor_gradient_probe(model_before, rows, advantages, False))
        assert probes['singleton']['actor_gradient_l2'] == 0.
        assert probes['multi_candidate']['actor_gradient_l2'] > 0.
        assert stats['max_old_logprob_error'] < 1e-4 and stats['max_old_value_error'] < 1e-4
        updates.append(dict(update=number, samples=len(rows), optimizer_steps=steps, delta=actual_delta,
            singleton_decisions=counts[1], multi_candidate_decisions=multi_count,
            candidate_count_histogram=dict(sorted(counts.items())), CPU_replay=stats,
            CPU_actor_gradient_probe=probes, episodes=episodes, native_target_statuses=dict(native_statuses)))
    assert not torch.cuda.is_initialized()
    assert_frozen(plan['hashes'])
    evidence = dict(passed=True, native_boundary_comparison_passed=True, stages=stages, updates=updates,
        audit_game_started=False, audit_optimizer_steps=0, audit_CUDA_initialized=False,
        historical_parent_sha256=plan['parent_checkpoint_sha256'],
        limitations='Training curriculum and exact boundary replay only. Repeated branches are duplicates, not independent games. '
                    'Singleton commitment supplies zero direct actor gradient; critic learning can still use those transitions. '
                    'CPU gradient probe is an archived-data diagnostic, not recorded CUDA minibatch gradients. '
                    'No independent strategic ability improvement certified.')
    atomic_json(args.out / 'AUDIT.json', evidence)
    snapshot = args.out / 'sources'
    snapshot.mkdir()
    shutil.copy2(Path(__file__), snapshot / Path(__file__).name)
    print(json.dumps(dict(passed=True, updates=[dict(update=update['update'], samples=update['samples'],
        singleton=update['singleton_decisions'], multi=update['multi_candidate_decisions'],
        actor_delta=update['delta']['actor'], replay=update['CPU_replay']) for update in updates]), indent=2))


if __name__ == '__main__':
    main()
