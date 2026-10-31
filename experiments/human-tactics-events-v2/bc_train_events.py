"""events-v2 exploratory BC on gated demonstrations.

Derivative of human-tactics-recovery-v2/train_bc.py (read-only reuse of the
frozen research recovered-graph.py and expert-knowledge-v1 codec).

Data gate (per task/demonstration schema):
  Q3-paired-verified : paired vs teacher with loss benefit AND mechanism
                       (main-force counter damage down) on the FROZEN test split
  Q2-ability-verified: legal trajectory, normal win, the selected ability attack
                       confirmed by native events (SECONDARY/primary damage landed)
No Q3 tactic exists for dragon/cloud (their experts did not validate); their
demonstrations stay Q2 and are explicitly NOT high-quality BC material.

Modes:
  --preflight : CPU-only encode/label validation (no GPU, no training)
  (default)   : CUDA policy-head BC, 60 steps, batch 16, lr 1e-4
"""
import argparse
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import time
import numpy as np
import torch
from lab_io import atomic_json

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parents[1] / 'research'
KNOWLEDGE = HERE.parents[1] / 'experiments' / 'expert-knowledge-v1'
B64 = Path('/root/heroes3-ai-lab/models/graph-finetune/1792068859379237126/update-64.pt')


def digest(path):
    import hashlib
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def load_demonstrations():
    spec = importlib.util.spec_from_file_location('codec', KNOWLEDGE / 'graph_observation_codec.py')
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    rows = [json.loads(line) for line in (HERE / 'demonstrations-v1.jsonl').read_text().splitlines()]
    observations, labels, metas = [], [], []
    for row in rows:
        assert row['expert_action'] in row['legal_action_ids'], 'demonstration action not legal'
        obs = codec.unpack(row['observation'], row['actor_side'])
        observations.append(obs)
        labels.append(row['legal_action_ids'].index(row['expert_action']))
        metas.append(dict(tier=row['quality_tier'], tactic=row['tactic_id'],
                          battle_id=row['battle_id'], policy_version=row['policy_version']))
    return observations, labels, metas


def frozen_artifacts():
    paths = list(HERE.glob('*.py')) + [KNOWLEDGE / 'graph_observation_codec.py',
                                       RESEARCH / 'recovered-graph.py', B64]
    return {str(p): digest(p) for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', default=str(B64))
    parser.add_argument('--output', required=True)
    parser.add_argument('--steps', type=int, default=60)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    output = Path(args.output)
    assert not output.exists(), 'Never overwrite prior model or BC report'
    checkpoint = Path(args.checkpoint)
    assert checkpoint.exists(), f'missing checkpoint: {checkpoint}'

    observations, labels, metas = load_demonstrations()
    tier_counts = {}
    for m in metas:
        tier_counts[m['tier']] = tier_counts.get(m['tier'], 0) + 1
    sides = sorted({obs['lab_side'] for obs in observations})
    print(f'demonstrations: {len(observations)} decisions, tiers={tier_counts}, sides={sides}')
    assert sides == [0, 1], 'both actor sides must be present'

    frozen = frozen_artifacts()

    spec = importlib.util.spec_from_file_location('bc_graph', RESEARCH / 'recovered-graph.py')
    graph = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(graph)

    if args.preflight:
        # CPU-only: encode in batches of 8 (same batch as CUDA path) and
        # validate shapes/labels; no GPU touched.
        pair = graph.RecoveredPair(str(checkpoint)).eval()
        cached = []
        for start in range(0, len(observations), 8):
            with torch.inference_mode():
                cached.extend(pair.encode_features(observations[start:start + 8]))
        assert len(cached) == len(labels)
        counts = {int(v): labels.count(v) for v in set(labels)}
        report = dict(completed=True, mode='cpu-preflight', samples=len(cached),
                      tier_counts=tier_counts, label_histogram=counts,
                      initial_checkpoint=str(checkpoint), initial_sha256=digest(checkpoint),
                      frozen_artifacts=frozen)
        atomic_json(output, report)
        print('preflight OK:', json.dumps({k: report[k] for k in
              ['samples', 'tier_counts', 'label_histogram']}))
        return

    with Path('/root/heroes3-ai-lab/evaluations/.pool-lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit() or int(entry.name) == os.getpid():
                continue
            try:
                command = (entry / 'cmdline').read_bytes().split(b'\0')
            except OSError:
                continue
            names = [Path(os.fsdecode(value)).name for value in command[:4]]
            assert not any(name.startswith(('train-graph-finetune', 'train-recovered-heads',
                                            'train-reference', 'train-conservative', 'run-mixed-v2'))
                           for name in names), 'Preserve one GPU learner'
        assert torch.cuda.is_available()
        torch.set_num_threads(2)
        torch.manual_seed(2026102901)
        pair = graph.RecoveredPair(str(checkpoint)).cuda().eval()
        started = time.monotonic()
        cached = []
        for start in range(0, len(observations), 8):
            cached.extend(pair.encode_features(observations[start:start + 8]))
        heads = [name for name, _ in pair.named_parameters() if 'policy_head__' in name]
        before = {name: parameter.detach().cpu().clone() for name, parameter in pair.named_parameters()}
        for name, parameter in pair.named_parameters():
            parameter.requires_grad_(name in heads)
        optimizer = torch.optim.Adam(
            [p for p in pair.parameters() if p.requires_grad], lr=1e-4)

        def loss_for(indices):
            batch = graph.head_collate([cached[i] for i in indices], 'cuda')
            logits, _ = pair(*batch)
            return torch.nn.functional.cross_entropy(
                logits, torch.tensor([labels[i] for i in indices], device='cuda'))

        def mean_loss():
            with torch.inference_mode():
                values = [float(loss_for(list(range(s, min(s + 16, len(cached))))))
                          * min(16, len(cached) - s)
                          for s in range(0, len(cached), 16)]
            return sum(values) / len(cached)

        initial = mean_loss()
        for _ in range(args.steps):
            indices = torch.randint(len(cached), (min(16, len(cached)),)).tolist()
            loss = loss_for(indices)
            assert torch.isfinite(loss)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(pair.parameters(), .5)
            assert torch.isfinite(norm)
            optimizer.step()
        final = mean_loss()
        changed = [name for name, parameter in pair.named_parameters()
                   if not torch.equal(before[name], parameter.detach().cpu())]
        assert changed and all(name in heads for name in changed), \
            'Only policy-head weights may change'
        assert frozen_artifacts() == frozen, 'Implementation changed during BC'

        bundle = dict(
            models={role: dict(weights={k.replace('__', '.'): v.detach().cpu()
                                        for k, v in model.weights.items()},
                               metadata=model.metadata)
                    for role, model in pair.models.items()},
            source='events-v2 gated demonstrations (Q3 test-mechanism + Q2 ability-verified)',
            algorithm='BC', finetuning_mode='heads', completed_updates=0, environment_steps=0,
            bc_steps=args.steps, config=vars(args), optimizer_state_dict=optimizer.state_dict(),
            torch_rng_state=torch.get_rng_state(), cuda_rng_states=torch.cuda.get_rng_state_all(),
            resume_note='BC optimizer is not a PPO optimizer; use a fresh PPO optimizer.')
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_name(output.name + '.tmp')
        assert not temporary.exists()
        torch.save(bundle, temporary)
        with temporary.open('rb') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, output)
        loaded = torch.load(output, map_location='cpu', weights_only=True)
        assert loaded['algorithm'] == 'BC'
        report = dict(
            completed=True, mode='cuda-bc', CUDA_training=True, checkpoint=str(output),
            sha256=digest(output), initial_checkpoint=str(checkpoint),
            initial_sha256=digest(checkpoint), samples=len(cached),
            tier_counts=tier_counts, demonstrations=str(HERE / 'demonstrations-v1.jsonl'),
            gradient_steps=args.steps, initial_training_nll=float(initial),
            final_training_nll=float(final), changed_policy_parameters=len(changed),
            graph_and_value_weights_unchanged=True,
            wall_seconds=time.monotonic() - started, frozen_artifacts=frozen,
            limitations='Exploratory BC on 205 gated decisions (62 Q3 + 143 Q2). '
                        'NLL fit does not prove battle improvement; paired evaluation '
                        'must follow on frozen scenarios.')
        atomic_json(output.with_suffix('.json'), report)
        print('BC done:', json.dumps({k: report[k] for k in
              ['samples', 'tier_counts', 'initial_training_nll', 'final_training_nll',
               'changed_policy_parameters']}))


if __name__ == '__main__':
    main()
