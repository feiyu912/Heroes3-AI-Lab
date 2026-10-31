# Model registry (weights not tracked)

The `.pt` / `.onnx` files in this directory are the lab's actual model artifacts
and are **not** committed to Git.  `MANIFEST.json` records every file's path,
byte size and SHA-256 at the time of the 2026-10-31 repository snapshot.

Important families:

| Family | Purpose | Notes |
|---|---|---|
| `selected-v3/`, `challenge-v4/`, `goal-v5-*` | battle models | historical challenge/v5 candidates; many are >30 MiB |
| `bc-balanced-v1/` | battle behavior cloning baselines | MLP/attention/GNN; BC fit only |
| `goal-v5-native-selected/`, `upstream-v15/` | exported ONNX battle runtimes | used by the native MMAI path |
| `graph-finetune/` (in the lab profile) | battle PPO checkpoints | not copied here; see experiment reports |
| `strategic-learned-recruitment-*` (in `experiments/`) | strategic schema6 models | prior-zero initialization, PPO updates, BC |

Do not infer strength from a checkpoint's presence or size.  Read the matching
`REVIEW.md` / `AUDIT.json` / independent DEV report and the final policy freeze
before promoting anything.
