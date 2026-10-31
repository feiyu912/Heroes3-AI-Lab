# Strategic BC (schema6) — preparation and offline trainer

Status: **pipeline ready; no expert dataset has been trained yet.** This directory
does not claim a stronger model. It exists so that the BC data prepared on the
other machine can be validated and trained without changing frozen PPO files.

## Why this package exists

The current strategic PPO loop trains from 8 complete episodes and performs one
PPO update (260–292 Adam steps).  Against `Nullkiller2` it has no winning
trajectories, so every chosen action in those games receives a negative
advantage.  Behavior cloning is a sensible way to inject a positive prior, but
only if the teacher data is real, legal, and aligned with the exact schema6
observation/action interface.

This package implements the offline half:

- strict dataset validation (`validate_dataset.py`);
- masked candidate cross-entropy with action-type balancing (`train_bc.py`);
- a self-describing `strategic-bc-checkpoint-v1` bundle;
- a fresh optimizer/RNG boundary (BC is not a PPO resume).

It deliberately **does not**:

- call `qualification.require_qualification()` (the old binding contains WSL
  paths);
- synthesize or "fill in" a video action;
- modify the frozen PPO trainer, encoder, model, or native binaries;
- claim that a lower NLL or higher top-1 is game strength.

## Dataset contract

One JSON object per line.  The minimal decision record is:

```json
{
  "request": {"schema": "strategy-candidates-v6", "...": "exact native request"},
  "action": 17,
  "action_type": "move",
  "episode_id": "train-map-01-p0-seed2026104402",
  "split": "train",
  "return": -1.0,
  "source": {"kind": "script", "trajectory_origin": "engine_execution",
             "creator": "video-derived rule teacher v1", "verified": false}
}
```

`action` is the **candidate index in that request**, never a global action id.
`return` is optional and only used for an auxiliary value loss.  A trajectory
wrapper is also accepted:

```json
{"record_type": "episode", "episode_id": "...", "split": "train",
 "decisions": [{"request": {...}, "action": 3}, ...]}
```

The exact request must validate with the frozen schema6 encoder and the pinned
150-creature catalog.  See `DATA_CONTRACT.md` for the full rules, including how
video-derived knowledge may and may not become labels.

## Validate

```bash
/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Ubuntu/native-gpu-verified-20261025/bin/python \
  validate_dataset.py --dataset /path/to/bc.jsonl --out /path/to/DATASET_AUDIT.json \
  --min-samples 10000 --require-split --quality-gate q2
```

Use `--quality-gate q3` only for data that has passed the project's Q3 evidence
gate.  Q2 is explicitly exploratory.

## Train

```bash
/home/kaicheng/Documents/Codex/2026-10-24/hello/outputs/Heroes3-Ubuntu/native-gpu-verified-20261025/bin/python \
  train_bc.py --dataset /path/to/bc-train.jsonl /path/to/bc-validation.jsonl \
  --out runs/strategic-bc-01 \
  --base ../takeover-20261023/active-learning-delivery-01/control-update-1.pt \
  --audit /path/to/DATASET_AUDIT.json \
  --device cuda --epochs 20 --batch-size 64 --lr 3e-4 \
  --val-fraction 0 --balance-alpha 0.5
```

`--val-fraction 0` is correct when the dataset already has explicit
train/validation files.  If it has no splits, use an episode-level holdout
(`--val-fraction 0.1`); never split individual decisions from the same episode.

On another machine without the project resource locks, add `--no-lock`.  On this
Ubuntu host, leave it out: the trainer takes the nonblocking GPU→pool locks when
the lock files exist.

The output is `runs/.../bc-checkpoint.pt` plus `TRAINING_REPORT.json` and
`DATASET_AUDIT.json`.  The checkpoint can be loaded with `bc_common.load_any_checkpoint`;
the current frozen `model_io` loader is intentionally **not** used because BC
weights are not a prior-zero initialization and are not a PPO resume.

## Required next gate

Offline fit is not a model promotion.  After BC:

1. export/load the policy into an isolated runtime broker (new loader, fresh
   PPO optimizer, same encoder/catalog);
2. paired native games vs `EmptyAI` and `Nullkiller2`, same maps/roles/seeds,
   at least 32 games per arm;
3. only then a bounded PPO fine-tune with a KL anchor to the BC policy (or an
   auxiliary BC loss).  Pure PPO on terminal ±1 with 8 games has already failed
   to produce a stable gain.

## Known incompatibilities to resolve before PPO

- `model_io.initialization_model` rejects non-zero `recruit_actor`/`recruit_bias`
  and requires the old prior-zero lineage.  A BC checkpoint will fail that check.
- `train_update_v3.py --resume` expects a PPO optimizer/protocol/RNG boundary;
  a BC optimizer is not a PPO optimizer.
- The runtime broker currently calls `model_io.load_model`; an isolated BC
  broker (or a new loader) is required.  Do not relabel a BC checkpoint as a PPO
  resume.
- The action space is still single-hero move/end_turn/build/recruit; video rules
  about multi-hero play, hero hiring, town management, army chains, or spells
  cannot be represented until those interfaces exist.
