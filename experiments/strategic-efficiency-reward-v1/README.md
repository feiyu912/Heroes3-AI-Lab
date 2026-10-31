# Matched-data efficiency reward epoch

Frozen CPU-ready candidate, 2026-10-20. No native/build/GPU/optimizer execution by this implementation task. Existing collection, native audit, CUDA admission, action schema, model architecture and original +/-1 PPO remain unchanged.

`targets.py` certifies the eight immutable shared admissions and derives separate learning returns. It checks the registered parent, seeds 2026102300..07, complete cells, original hash chains and native audit epoch. `TARGETS.json` binds the complete source closure, arm protocol, original rows, and every real request/native ID/calendar proof. Only `verify_targets()` followed by `load_targets()` authenticates raw evidence; `validate_derived_sample()` alone is a local consistency gate, not independent native certification.

Calendar evidence comes from the whole-game-audited client.log SHA: server `Turn n` and `Info about turn n has been sent!`, client-applied NewTurn, received PlayerStartsTurn, every request SHA/native send binding, and actual own-player terminal callback/typed mirror. The typed game_over has no calendar day. Terminal day is not inferred from own_turn or the last policy request. CGameHandler's Turn marker and NewTurnProcessor's `day+1`/`n.day` semantics are bound to the actual capsule compiled manifest: use capsule source-snapshot where available and require the accepted source's full SHA to match compiled manifest for remaining files. No unbound strategy trace is used.

`prepare_private.py` produces the reviewable `.diff` files. The private PPO only replaces the +/-1 gate with the registered derived-target gate and changes protocol labels. The objective and optimizer loop source are identical to the original. Original prepare continues to reject fractional treatment returns. Train entry requires initialization d590..., reset Adam, seed 2026102300 and exactly the shared eight admissions; it canonically loads TARGETS episode order so both arms shuffle identical rows. It permits one new CUDA update, no resume. KL safety can make actual step counts differ. Checkpoints use unchanged model_io and purpose `curriculum_training`.

Actual CPU preparation already passed:

- `/root/heroes3-ai-lab/evaluations/strategic-efficiency-targets-01/TARGETS.json`: eight certified games / 2111 original rows.
- `CPU_REPORT.json`: control prepared tensors, metadata, every 64-row minibatch objective, and full-batch accumulated parameter gradients bit-exact against original PPO; no optimizer instantiated/stepped. Formula, protocol, source-subset, parent, arm, forged calendar and target negatives rejected.
- Python syntax/import and train `--help` passed. This is not CUDA training or checkpoint qualification; root executes those next.

Do not regenerate or edit any Python/PLAN source after freeze. Changing any source invalidates TARGETS and requires a new derived artifact before running either arm. Original sampling artifacts remain immutable.

WSL CPU verification (safe to rerun):

```bash
CUDA_VISIBLE_DEVICES='' /root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-efficiency-reward-v1/targets.py --verify /root/heroes3-ai-lab/evaluations/strategic-efficiency-targets-01
```

Root-only CUDA commands, run control then treatment serially, with separate fresh output directories:

```bash
PY=/root/heroes3-ai-lab/gpu-venv/bin/python
ENTRY=/mnt/g/Heroes3-AI-Lab/experiments/strategic-efficiency-reward-v1/train_efficiency.py
INITIAL=/mnt/g/Heroes3-AI-Lab/experiments/strategic-learning-mainline-20261020/temperature-initialization-01/temperature-2-initialization.pt
SHARED=/root/heroes3-ai-lab/evaluations/strategic-efficiency-shared-train-01
TARGETS=/root/heroes3-ai-lab/evaluations/strategic-efficiency-targets-01
CAPSULE=/root/heroes3-ai-lab/evaluations/typed-director-terminal-drain-capsule-03
ADMISSIONS=()
for cell in 00 01 02 03 04 05 06 07; do ADMISSIONS+=(--admission "$SHARED/cell-$cell/admitted"); done
"$PY" "$ENTRY" --initialize "$INITIAL" --arm control --targets "$TARGETS" "${ADMISSIONS[@]}" --capsule "$CAPSULE" --seed 2026102300 --purpose curriculum_training --out /root/heroes3-ai-lab/evaluations/strategic-efficiency-control-update-01
"$PY" "$ENTRY" --initialize "$INITIAL" --arm treatment --targets "$TARGETS" "${ADMISSIONS[@]}" --capsule "$CAPSULE" --seed 2026102300 --purpose curriculum_training --out /root/heroes3-ai-lab/evaluations/strategic-efficiency-treatment-update-01
```

After each update root must run the existing independent CUDA checkpoint audit, record actual steps/KL stop/readback, then the already registered paired DEV comparison. CPU equality does not certify CUDA equivalence or ability improvement. Reward is the sole planned learning factor; no economy action implementation was added.
