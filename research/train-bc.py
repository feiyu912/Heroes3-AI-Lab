import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time
try:
    import resource
except ImportError:
    resource = None
import numpy as np
import torch
from decision_model import DecisionModel, collate, load_dataset, save_model, load_model

parser = argparse.ArgumentParser()
parser.add_argument('--dataset', default='/root/heroes3-ai-lab/datasets/teacher-v1')
parser.add_argument('--epochs', type=int, default=16)
parser.add_argument('--batch-size', type=int, default=32)
parser.add_argument('--seed', type=int, default=20261014)
parser.add_argument('--architectures', nargs='+', default=['mlp', 'attention', 'gnn'])
parser.add_argument('--output', default='/mnt/g/Heroes3-AI-Lab/research/bc-baseline-v1.json')
parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
parser.add_argument('--model-dir', default='/root/heroes3-ai-lab/models/bc-v1')
parser.add_argument('--deduplicate', action='store_true')
parser.add_argument('--width', type=int, default=128)
parser.add_argument('--no-value-head', action='store_true')
args = parser.parse_args()
torch.set_num_threads(2)
torch.set_num_interop_threads(1)
dataset = {split: load_dataset(args.dataset, split) for split in ['train', 'validation', 'test']}
if args.deduplicate:
    for split, samples in dataset.items():
        unique = {}
        for sample in samples:
            unique.setdefault(sample['state_hash'], sample)
        dataset[split] = list(unique.values())
manifest_hash = hashlib.sha256((Path(args.dataset) / 'manifest.json').read_bytes()).hexdigest()


def evaluate(model, samples):
    model.eval()
    total_loss = correct = top3 = value_error = 0
    by_type = {}
    latencies = []
    with torch.inference_mode():
        for start in range(0, len(samples), args.batch_size):
            batch = samples[start:start + args.batch_size]
            inputs = collate([b['features'] for b in batch], args.device)
            before = time.perf_counter()
            logits, values = model(*inputs)
            latencies.append((time.perf_counter() - before) * 1000)
            labels = torch.tensor([b['label'] for b in batch], device=args.device)
            targets = torch.tensor([b['value'] for b in batch], device=args.device)
            assert torch.isfinite(logits[inputs[-1]]).all() and torch.isfinite(values).all()
            prediction = logits.argmax(1)
            hits = prediction == labels
            total_loss += torch.nn.functional.cross_entropy(logits, labels, reduction='sum').item()
            correct += hits.sum().item()
            k = min(3, logits.shape[1])
            top3 += (logits.topk(k, 1).indices == labels[:, None]).any(1).sum().item()
            value_error += ((values - targets) ** 2).sum().item()
            for b, hit in zip(batch, hits.tolist()):
                row = by_type.setdefault(str(b['action_type']), dict(samples=0, correct=0))
                row['samples'] += 1
                row['correct'] += int(hit)
    return dict(samples=len(samples), top1=correct / len(samples), top3=top3 / len(samples),
                masked_cross_entropy=total_loss / len(samples), value_mse=value_error / len(samples),
                per_action_type=by_type, batch_forward_ms_p50=float(np.median(latencies)))


results = []
for architecture in args.architectures:
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    width = 64 if architecture == 'mlp64' else args.width
    value_enabled = not (args.no_value_head or architecture == 'mlp-no-value')
    base_architecture = 'mlp' if architecture in ['mlp64', 'mlp-no-value'] else architecture
    model = DecisionModel(base_architecture, width, value_enabled).to(args.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)
    parameter_count = sum(p.numel() for p in model.parameters())
    initial = evaluate(model, dataset['validation'])
    checkpoint_path = str(Path(args.model_dir) / f'{architecture}.pt')
    best = float('inf')
    history = []
    started = time.monotonic()
    for epoch in range(args.epochs):
        model.train()
        indices = rng.permutation(len(dataset['train']))
        losses = []
        for start in range(0, len(indices), args.batch_size):
            batch = [dataset['train'][i] for i in indices[start:start + args.batch_size]]
            inputs = collate([b['features'] for b in batch], args.device)
            logits, value = model(*inputs)
            labels = torch.tensor([b['label'] for b in batch], device=args.device)
            targets = torch.tensor([b['value'] for b in batch], device=args.device)
            loss = torch.nn.functional.cross_entropy(logits, labels)
            if value_enabled:
                loss = loss + 0.1 * ((value - targets) ** 2).mean()
            assert torch.isfinite(loss)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            assert torch.isfinite(norm)
            optimizer.step()
            losses.append(loss.item())
        validation = evaluate(model, dataset['validation'])
        history.append(dict(epoch=epoch + 1, training_loss=float(np.mean(losses)), validation=validation))
        if validation['masked_cross_entropy'] < best:
            best = validation['masked_cross_entropy']
            save_model(model, checkpoint_path, epoch=epoch + 1, seed=args.seed,
                       dataset_manifest_sha256=manifest_hash, source='BattleAI BC',
                       optimizer_state_dict=optimizer.state_dict())
        print(architecture, epoch + 1, 'validation top1', round(validation['top1'], 4), flush=True)
    restored, checkpoint = load_model(checkpoint_path)
    restored.to(args.device)
    record = dict(architecture=architecture, parameter_count=parameter_count,
                  checkpoint=checkpoint_path, checkpoint_sha256=hashlib.sha256(Path(checkpoint_path).read_bytes()).hexdigest(),
                  best_epoch=checkpoint['epoch'], initial_validation=initial,
                  width=width, value_enabled=value_enabled,
                  train=evaluate(restored, dataset['train']), validation=evaluate(restored, dataset['validation']),
                  test=evaluate(restored, dataset['test']), training_seconds=time.monotonic()-started,
                  history=history)
    # A second independent load must reproduce scores, not just load without an exception.
    reloaded, _ = load_model(checkpoint_path)
    reloaded.to(args.device)
    with torch.inference_mode():
        inputs = collate([dataset['test'][0]['features']], args.device)
        a, va = restored(*inputs)
        b, vb = reloaded(*inputs)
        assert torch.equal(a, b) and torch.equal(va, vb)
    record['checkpoint_reload_identical'] = True
    results.append(record)
    Path(args.output).write_text(json.dumps(dict(seed=args.seed, epochs=args.epochs,
                                               batch_size=args.batch_size, torch_version=torch.__version__,
                                               dataset_manifest_sha256=manifest_hash,
                                               device=args.device, deduplicated=args.deduplicate,
                                               peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 if resource else None,
                                               results=results), indent=2))
print('BC COMPLETE', args.output, flush=True)
