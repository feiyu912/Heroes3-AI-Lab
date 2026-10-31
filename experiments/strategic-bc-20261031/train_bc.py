"""Masked behavior cloning for the schema6 strategic candidate scorer.

This is an offline trainer, not PPO.  It starts a fresh optimizer/RNG epoch from
an initialization or PPO checkpoint, fits candidate-level expert labels, and
writes a self-describing ``strategic-bc-checkpoint-v1`` bundle.  A separate
PPO gate must convert that bundle into a runtime policy; fit metrics are not a
strength claim.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import random
import signal
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import torch
import torch.nn.functional as F

from bc_common import (
    CATALOG_SHA256, DEFAULT_INITIAL, RESOURCE, atomic_torch_save, configure_catalog,
    encoder, load_any_checkpoint, make_bc_bundle, read_jsonl, sha256, tensor_sha, write_json,
)
from validate_dataset import canonical_request, normalize


def acquire_locks(enabled: bool):
    if not enabled:
        return []
    handles = []
    for name in (".gpu-learner-lock", ".pool-lock"):
        path = RESOURCE / name
        if not path.is_file():
            print(f"WARNING: lock file missing, continuing without {name}: {path}", file=sys.stderr)
            continue
        handle = path.open("r+")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            raise RuntimeError(f"resource lock is held: {path}")
        handles.append(handle)
    return handles


def release_locks(handles):
    for handle in reversed(handles):
        try:
            fcntl.flock(handle, fcntl.LOCK_UN)
        finally:
            handle.close()


def load_dataset(paths, catalog, *, min_samples=1):
    files = []
    for item in paths:
        if item.is_dir():
            files.extend(sorted(item.rglob("*.jsonl")))
        else:
            files.append(item)
    files = sorted({path.resolve() for path in files})
    records, errors, seen = [], [], {}
    for path in files:
        for number, row in enumerate(read_jsonl(path), 1):
            try:
                items = normalize(path, row, catalog)
            except ValueError as error:
                errors.append(f"{path}:{number}: {error}")
                continue
            for item in items:
                request = item.get("request")
                try:
                    encoder.validate(request, catalog=catalog)
                except (ValueError, TypeError) as error:
                    errors.append(f"{path}:{number}: {error}")
                    continue
                action = item.get("action", item.get("selected_index"))
                if type(action) is not int or not 0 <= action < len(request["candidates"]):
                    errors.append(f"{path}:{number}: action out of range")
                    continue
                action_type = item.get("action_type", request["candidates"][action]["op"])
                if action_type != request["candidates"][action]["op"]:
                    errors.append(f"{path}:{number}: action_type mismatch")
                    continue
                if request.get("creature_catalog_sha256") != CATALOG_SHA256:
                    errors.append(f"{path}:{number}: catalog mismatch")
                    continue
                episode_id = item.get("episode_id")
                if not isinstance(episode_id, (str, int)) or str(episode_id) == "":
                    errors.append(f"{path}:{number}: episode_id required")
                    continue
                split = item.get("split", "unspecified")
                if split == "val":
                    split = "validation"
                if split not in ("train", "validation", "test", "unspecified"):
                    errors.append(f"{path}:{number}: bad split {split!r}")
                    continue
                key = canonical_request(request)
                if key in seen:
                    if seen[key] != action:
                        errors.append(f"{path}:{number}: conflicting duplicate state (first label {seen[key]}, now {action})")
                    continue
                seen[key] = action
                value = item.get("return", item.get("value"))
                if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value))):
                    errors.append(f"{path}:{number}: nonfinite return/value")
                    continue
                records.append(dict(
                    request=request, action=action, action_type=action_type,
                    episode_id=str(episode_id), split=split, value=value,
                    file=str(path), request_sha256=key,
                ))
    if errors:
        raise ValueError("dataset validation failed:\n" + "\n".join(errors[:50]))
    if len(records) < min_samples:
        raise ValueError(f"only {len(records)} unique decisions; min-samples={min_samples}")
    return records, files


def split_records(records, *, val_fraction: float, seed: int):
    if val_fraction <= 0:
        return [r for r in records if r["split"] != "test"], [], [r for r in records if r["split"] == "test"]
    explicit_val = [r for r in records if r["split"] == "validation"]
    explicit_test = [r for r in records if r["split"] == "test"]
    train_pool = [r for r in records if r["split"] == "train"]
    unspecified = [r for r in records if r["split"] == "unspecified"]
    if explicit_val:
        return train_pool + unspecified, explicit_val, explicit_test
    if not train_pool and not unspecified:
        raise ValueError("no train/unspecified records")
    pool = train_pool + unspecified
    episodes = sorted({r["episode_id"] for r in pool})
    if len(episodes) < 2:
        raise ValueError("episode-level validation split requires at least two episodes; pass --val-fraction 0 for a fit-only smoke run")
    ranked = sorted(episodes, key=lambda e: hashlib.sha256(f"{seed}:{e}".encode()).hexdigest())
    count = max(1, min(len(ranked) - 1, round(len(ranked) * val_fraction)))
    held = set(ranked[:count])
    return [r for r in pool if r["episode_id"] not in held], [r for r in pool if r["episode_id"] in held], explicit_test


def sample_weights(records, alpha: float, cap: float):
    counts = Counter(r["action_type"] for r in records)
    total = sum(counts.values())
    weights = {}
    for action_type, count in counts.items():
        weights[action_type] = min(cap, (total / (len(counts) * count)) ** alpha) if count else 1.0
    return weights


def collate(samples, device):
    batch = encoder.collate([s["request"] for s in samples], device)
    labels = torch.tensor([s["action"] for s in samples], dtype=torch.long, device=device)
    weights = torch.tensor([s["weight"] for s in samples], dtype=torch.float32, device=device)
    values = torch.tensor([float(s["value"]) if s["value"] is not None else 0.0 for s in samples],
                          dtype=torch.float32, device=device)
    has_value = torch.tensor([s["value"] is not None for s in samples], dtype=torch.bool, device=device)
    return batch, labels, weights, values, has_value


@torch.no_grad()
def evaluate(model, records, device, batch_size=128):
    model.eval()
    if not records:
        return dict(samples=0, top1=None, top3=None, nll=None, value_mse=None, per_action_type={})
    total_nll = total_correct = total_top3 = total = 0
    total_value = 0.0
    value_n = 0
    per_type = defaultdict(lambda: dict(samples=0, correct=0, top3=0, nll=0.0))
    for start in range(0, len(records), batch_size):
        batch_records = records[start:start + batch_size]
        batch, labels, weights, values, has_value = collate(batch_records, device)
        logits, predicted_values = model(**batch)
        nll = F.cross_entropy(logits, labels, reduction="none")
        predictions = logits.argmax(-1)
        k = min(3, logits.shape[1])
        top3 = (logits.topk(k, dim=1).indices == labels[:, None]).any(dim=1)
        total_nll += float(nll.sum())
        total_correct += int((predictions == labels).sum())
        total_top3 += int(top3.sum())
        total += len(batch_records)
        if bool(has_value.any()):
            mask = has_value.float()
            total_value += float(((predicted_values - values).square() * mask).sum())
            value_n += int(mask.sum())
        for record, nll_value, correct, hit3 in zip(batch_records, nll.tolist(), (predictions == labels).tolist(), top3.tolist()):
            row = per_type[record["action_type"]]
            row["samples"] += 1
            row["correct"] += int(correct)
            row["top3"] += int(hit3)
            row["nll"] += float(nll_value)
    for row in per_type.values():
        row["top1"] = row["correct"] / row["samples"]
        row["top3"] = row["top3"] / row["samples"]
        row["nll"] = row["nll"] / row["samples"]
    return dict(
        samples=total,
        top1=total_correct / total if total else None,
        top3=total_top3 / total if total else None,
        nll=total_nll / total if total else None,
        value_mse=total_value / value_n if value_n else None,
        per_action_type=dict(per_type),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base", type=Path, default=None, help="initialization or PPO checkpoint; default prefers the tested control update")
    parser.add_argument("--audit", type=Path, default=None, help="optional DATASET_AUDIT.json to bind")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--value-weight", type=float, default=0.1)
    parser.add_argument("--balance-alpha", type=float, default=0.5)
    parser.add_argument("--balance-cap", type=float, default=5.0)
    parser.add_argument("--val-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=2026103101)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--min-samples", type=int, default=1000)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--no-lock", action="store_true")
    parser.add_argument("--deterministic", action="store_true")
    args = parser.parse_args()

    catalog = configure_catalog()
    records, files = load_dataset(args.dataset, catalog, min_samples=args.min_samples)
    if args.max_samples and len(records) > args.max_samples:
        records = records[: args.max_samples]
    train, validation, test = split_records(records, val_fraction=args.val_fraction, seed=args.seed)
    if not train:
        raise ValueError("no training records after split")
    type_weights = sample_weights(train, args.balance_alpha, args.balance_cap)
    for record in records:
        record["weight"] = type_weights.get(record["action_type"], 1.0)
    summary = dict(
        files={str(path): sha256(path) for path in files},
        catalog_sha256=CATALOG_SHA256,
        encoder_version=encoder.ENCODER_VERSION,
        records=len(records), train=len(train), validation=len(validation), test=len(test),
        train_episodes=len({r["episode_id"] for r in train}),
        validation_episodes=len({r["episode_id"] for r in validation}),
        train_action_counts=dict(Counter(r["action_type"] for r in train)),
        validation_action_counts=dict(Counter(r["action_type"] for r in validation)),
        action_type_weights={key: float(value) for key, value in type_weights.items()},
        limitations=[
            "offline fit only; no native game, no PPO update, no promotion",
            "video-derived labels must be engine-executed reconstructions or verified human traces",
        ],
    )
    print(json.dumps(summary, indent=2))
    if args.preflight:
        print("PREFLIGHT ONLY: no model, no optimizer, no checkpoint", file=sys.stderr)
        return 0

    if args.out.exists():
        raise SystemExit(f"refusing to overwrite existing output: {args.out}")
    args.out.mkdir(parents=True, exist_ok=False)
    base = args.base
    if base is None:
        from bc_common import DEFAULT_UPDATED, DEFAULT_UPDATED_SHA256
        base = DEFAULT_UPDATED if DEFAULT_UPDATED.is_file() and sha256(DEFAULT_UPDATED) == DEFAULT_UPDATED_SHA256 else DEFAULT_INITIAL
    if not base.is_file():
        raise SystemExit(f"missing base checkpoint: {base}")
    base_sha = sha256(base)
    audit_sha = sha256(args.audit) if args.audit and args.audit.is_file() else None

    locks = acquire_locks(not args.no_lock)
    try:
        torch.set_num_threads(1)
        if args.deterministic:
            torch.use_deterministic_algorithms(True)
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
        random.seed(args.seed)
        torch.manual_seed(args.seed)
        if args.device.startswith("cuda"):
            torch.cuda.manual_seed_all(args.seed)
        model, base_bundle, loaded_sha = load_any_checkpoint(base, args.device)
        if loaded_sha != base_sha:
            raise ValueError("base checkpoint changed during load")
        model.train()
        optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
        best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
        best = dict(epoch=0, validation=None)
        history = []
        rng = random.Random(args.seed)
        patience = 0
        started = time.monotonic()
        for epoch in range(1, args.epochs + 1):
            order = list(range(len(train)))
            rng.shuffle(order)
            model.train()
            losses = []
            for start in range(0, len(order), args.batch_size):
                indices = order[start:start + args.batch_size]
                samples = [train[index] for index in indices]
                batch, labels, weights, values, has_value = collate(samples, args.device)
                logits, predicted_values = model(**batch)
                nll = F.cross_entropy(logits, labels, reduction="none")
                loss = (nll * weights).sum() / weights.sum().clamp_min(1e-8)
                if args.value_weight > 0 and bool(has_value.any()):
                    mask = has_value.float()
                    value_loss = ((predicted_values - values).square() * mask).sum() / mask.sum().clamp_min(1.0)
                    loss = loss + args.value_weight * value_loss
                if not bool(torch.isfinite(loss)):
                    raise ValueError("nonfinite BC loss")
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
                if not bool(torch.isfinite(norm)):
                    raise ValueError("nonfinite BC gradient")
                optimizer.step()
                losses.append(float(loss.detach()))
            validation_metrics = evaluate(model, validation, args.device, args.batch_size)
            train_metrics = evaluate(model, train, args.device, args.batch_size)
            row = dict(epoch=epoch, train_loss=sum(losses) / max(1, len(losses)), train=train_metrics, validation=validation_metrics)
            history.append(row)
            print(json.dumps({"epoch": epoch, "train_loss": row["train_loss"],
                              "val_nll": validation_metrics["nll"], "val_top1": validation_metrics["top1"]}), flush=True)
            score = validation_metrics["nll"]
            if score is not None and (best["validation"] is None or score < best["validation"]["nll"]):
                best = dict(epoch=epoch, validation=validation_metrics, train=train_metrics)
                best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
                patience = 0
            else:
                if validation:
                    patience += 1
                    if patience >= args.patience:
                        print(f"early stopping at epoch {epoch}", file=sys.stderr)
                        break
        if validation:
            model.load_state_dict(best_state, strict=True)
        else:
            # Fit-only smoke runs have no validation signal.  Keep the last
            # epoch rather than silently returning the untrained base weights.
            best = dict(epoch=len(history), validation=None, train=None)
        final_train = evaluate(model, train, args.device, args.batch_size)
        final_validation = evaluate(model, validation, args.device, args.batch_size)
        final_test = evaluate(model, test, args.device, args.batch_size) if test else None
        config = dict(
            dataset=[str(path) for path in files], dataset_hashes={str(path): sha256(path) for path in files},
            base_checkpoint=str(base), base_checkpoint_sha256=base_sha, audit=str(args.audit) if args.audit else None,
            audit_sha256=audit_sha, device=args.device, epochs=args.epochs, batch_size=args.batch_size,
            lr=args.lr, value_weight=args.value_weight, balance_alpha=args.balance_alpha, balance_cap=args.balance_cap,
            val_fraction=args.val_fraction, seed=args.seed, torch_version=str(torch.__version__),
            cuda_version=torch.version.cuda, deterministic=args.deterministic,
        )
        metrics = dict(best_epoch=best["epoch"], best=best, final_train=final_train,
                       final_validation=final_validation, final_test=final_test,
                       history=history, wall_seconds=time.monotonic() - started)
        bundle = make_bc_bundle(
            model, base_checkpoint_sha256=base_sha, dataset_audit_sha256=audit_sha or "",
            config=config, metrics=metrics,
            lineage=dict(
                source="strategic schema6 behavior cloning",
                base_checkpoint=str(base),
                reset_optimizer=True, reset_rng=True, discard_rollout=True, weights_only=True,
                not_an_ability_evaluation=True,
            ),
        )
        checkpoint = args.out / "bc-checkpoint.pt"
        checkpoint_sha = atomic_torch_save(bundle, checkpoint)
        report = dict(
            schema="strategic-bc-training-report-v1", completed=True, checkpoint=str(checkpoint),
            checkpoint_sha256=checkpoint_sha, base_checkpoint=str(base), base_checkpoint_sha256=base_sha,
            summary=summary, config=config, metrics=metrics, ability_improvement_claim=False,
            next_gate="PPO runtime integration + paired native evaluation; fit metrics are not strength",
        )
        write_json(args.out / "TRAINING_REPORT.json", report)
        write_json(args.out / "DATASET_AUDIT.json", summary)
        print(json.dumps({key: report[key] for key in ("completed", "checkpoint_sha256", "ability_improvement_claim")}, indent=2))
    finally:
        release_locks(locks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
