# Heroes III AI Lab

Research lab for a full-game **Heroes of Might and Magic III** AI on top of
[VCMI](https://github.com/vcmi/vcmi).  The project studies two connected
problems:

1. **Strategic / adventure-map play** — exploration, economy, building,
   recruitment, hero movement, army supply and full-map victory.
2. **Local battle play** — a learned combat policy that can beat the public
   MMAI agent and approach/exceed the native `BattleAI`.

The current code is an evidence-driven research repository, not a finished game
AI.  Models are only promoted after a frozen, independent evaluation; training
loss, teacher top-1 accuracy and small-sample win rates are not treated as proof
of strength.

## Current status

| Track | Current evidence | Honest status |
|---|---|---|
| Strategic PPO | 8 fresh TRAIN games / one PPO update per experiment; 4/4 vs EmptyAI, 0/4 vs Nullkiller2 | No stable strategic gain; no promotion |
| Strategic BC | schema6 candidate-scorer BC pipeline prepared (`experiments/strategic-bc-20261031/`) | Pipeline tested; no expert dataset trained yet |
| Local battle | 68 updates / 8,704 Adam; 15/16 vs BattleAI, 13–14/16 vs public MMAI in the latest 96-game comparison | Strong but not 95%; no net gain from recent terminal-credit/LR variants |
| Full game | single-hero move/build/recruit policy; native BattleAI for battles; scripted free transfers | Multi-hero, town-only neural control, hero hiring and full 1v7 remain open |

The most recent synthesis is **[BC_INTEGRATION_20261031.md](BC_INTEGRATION_20261031.md)**.
It explains why the strategic PPO is stuck, what behavior cloning can and cannot
fix, and the exact data contract for the BC preparation being done on another
machine.

## Key documents

- [NEW_CHAT_HANDOFF_20261023.md](NEW_CHAT_HANDOFF_20261023.md) — full goal,
  authorization, frozen protections and historical evidence index.
- [NEW_CHAT_HANDOFF_20261025_UBUNTU.md](NEW_CHAT_HANDOFF_20261025_UBUNTU.md) —
  native Ubuntu migration/recovery state.
- [NEW_CHAT_HANDOFF_20261026_UBUNTU.md](NEW_CHAT_HANDOFF_20261026_UBUNTU.md) —
  latest short handoff (refill mechanism, remaining goal).
- [BC_INTEGRATION_20261031.md](BC_INTEGRATION_20261031.md) — training diagnosis
  and BC feasibility.
- [experiments/strategic-bc-20261031/](experiments/strategic-bc-20261031/) —
  schema6 BC validator/trainer and data contract.
- [GOAL_ACTIVE.md](GOAL_ACTIVE.md), [CURRENT_PROGRESS_20261018_TAKEOVER.md](CURRENT_PROGRESS_20261018_TAKEOVER.md)
  — long-form historical progress.
- [experiments/takeover-20261023/INDEPENDENT_RESULTS_20261024.md](experiments/takeover-20261023/INDEPENDENT_RESULTS_20261024.md)
  — strategic/battle independent results before the Ubuntu continuation.
- [experiments/ubuntu-native-takeover-20261025/REPORT.md](experiments/ubuntu-native-takeover-20261025/REPORT.md)
  — native environment recovery, battle regression and learner recovery.

## Repository layout

```
research/        Core training/evaluation scripts and historical reports
experiments/     Isolated experiment packages, mostly source + reports + audits
models/          Model manifests; weights are deliberately not in Git
vcmi/            Upstream VCMI checkout (separate Git repository; not vendored)
.research/       Personal/unrelated material; excluded from the public repo
```

Because the full lab contains tens of gigabytes of raw native logs, maps, model
rollouts and repaired filesystem copies, this repository contains **source,
reports, manifests and audit summaries**, not the raw evidence tree.  See
[REPO_EXCLUSIONS.md](REPO_EXCLUSIONS.md) and [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
for what is present, what is excluded, and where the original artifacts live.

## BC data flow (other machine → this lab)

1. Prepare expert knowledge as either:
   - a deterministic `teacher(request) -> candidate index` implementation that
     is executed in the real isolated engine, or
   - a verified `human_recorded` trajectory.
2. Export exact schema6 requests and candidate indices as JSONL
   (see `experiments/strategic-bc-20261031/DATA_CONTRACT.md`).
3. Validate:
   ```bash
   python experiments/strategic-bc-20261031/validate_dataset.py \
     --dataset /path/to/bc.jsonl --out /path/to/DATASET_AUDIT.json \
     --min-samples 10000 --require-split --quality-gate q2
   ```
4. Train:
   ```bash
   python experiments/strategic-bc-20261031/train_bc.py \
     --dataset /path/to/bc-train.jsonl /path/to/bc-validation.jsonl \
     --out runs/strategic-bc-01 --audit /path/to/DATASET_AUDIT.json \
     --device cuda --epochs 20 --batch-size 64
   ```
5. Only after paired native evaluation, consider BC-initialized PPO with a new
   Adam/RNG boundary and a KL/auxiliary BC anchor.

Video commentary is **not** a label.  Guessed actions are rejected
(`video_guess`); the project's historical BC failures are preserved in
`experiments/human-tactics-events-v2/` and `experiments/human-tactics-events-v3/`.

## Environment

The original lab used WSL2; the current native-Ubuntu recovery is documented in
`experiments/ubuntu-native-takeover-20261025/`.  Runtime pieces remain in
isolated profiles and are not part of this Git repository:

- VCMI engine + the `DirectorAI`/gym connector (separate source tree),
- game data / maps (`Data`, `Mods`, `*.vmap`),
- Python GPU profile with PyTorch, ONNX Runtime and the exact frozen binaries,
- trained checkpoints and raw native evidence.

Resource discipline: one GPU learner, GPU lock then shared pool lock, nonblocking
and inherited by child processes.  Never delete lock files; release the advisory
locks instead.  See the handoff documents for the exact paths and frozen SHA
values.

## Third-party notices

- VCMI is GPL-2.0; the `vcmi/` directory is an upstream checkout and is not
  relicensed by this repository.
- Heroes of Might and Magic III game assets are not included.  Do not commit
  game data, maps, videos, or extracted media.
- Research documents may quote short public sources; media files and full
  transcripts are not redistributed.

## Contributing

This is a single-machine research lab with strict evidence rules.  Before adding
a new training result, read `NEW_CHAT_HANDOFF_20261023.md` and the relevant
`experiments/*/PLAN.md`.  New fixes should be isolated, hash-pinned and preserve
failed evidence rather than overwriting it.
