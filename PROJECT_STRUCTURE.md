# Project structure (full lab, 2026-10-31)

This file describes the **on-disk research lab**, not only the files tracked by Git.
Git contains source, reports, manifests and audit summaries. Raw native logs, game data,
model weights, capsule binaries and repaired filesystem copies stay on disk. See
`REPO_EXCLUSIONS.md` for the policy.

## Top level

| Directory | Files | Subdirs | Size | Git? |
|---|---:|---:|---:|---|
| `research/` | 913 | 53 | 131.0MiB | yes (filtered) |
| `experiments/` | 394,503 | 18,700 | 21.9GiB | yes (filtered) |
| `models/` | 48 | 10 | 1.0GiB | weights/manifests only |
| `vcmi/` | 4,113 | 439 | 51.6MiB | excluded |
| `maintenance/` | 9 | 1 | 4.6MiB | yes (filtered) |
| `handoff/` | 568 | 31 | 172.3MiB | yes (filtered) |
| `.research/` | 16 | 1 | 463.8KiB | excluded |
| `.git/` | 5,996 | 264 | 30.2MiB | yes (filtered) |
| `.workbuddy-ai/` | 2 | 1 | 9.6KiB | yes (filtered) |

| Package | Files | Subdirs | Size |
|---|---:|---:|---:|
| `experiments/battle-diverse-curriculum-20261020/` | 738 | 699 | 5.1GiB |
| `experiments/ubuntu-native-takeover-20261025/` | 5,922 | 943 | 4.8GiB |
| `experiments/takeover-20261023/` | 131,189 | 4,199 | 3.7GiB |
| `experiments/strategic-vector-v1/` | 53,574 | 1,428 | 907.6MiB |
| `experiments/strategic-typed-native-v1/` | 8,075 | 452 | 879.4MiB |
| `experiments/strategic-typed-training-v1/` | 39,610 | 1,750 | 864.1MiB |
| `experiments/strategic-learning-mainline-20261020/` | 39,628 | 1,526 | 848.3MiB |
| `experiments/strategic-learned-free-transfer-run-v1/` | 29,567 | 1,376 | 746.3MiB |
| `experiments/strategic-threat-replan-v2/` | 18,075 | 997 | 431.4MiB |
| `experiments/strategic-request-bind-barrier-v2/` | 16,612 | 777 | 427.6MiB |
| `experiments/strategic-director-terminal-drain-v3/` | 8,009 | 490 | 328.5MiB |
| `experiments/strategic-director-terminal-drain-v4/` | 15,237 | 861 | 299.5MiB |
| `experiments/strategic-refill-boundaries-20261026/` | 6,993 | 657 | 273.5MiB |
| `experiments/expert-knowledge-v1/` | 144 | 14 | 249.7MiB |
| `experiments/battle-family-curriculum-20261020/` | 36 | 4 | 234.6MiB |
| `experiments/strategic-refill-paired-build-20261026/` | 4,252 | 396 | 227.9MiB |
| `experiments/battle-training-resume-20261020-v2/` | 27 | 3 | 221.9MiB |
| `experiments/strategic-learned-build-exploration-run-v1/` | 188 | 52 | 200.2MiB |
| `experiments/human-tactics-events-v2/` | 965 | 12 | 174.1MiB |
| `experiments/multihero-mechanism-probe-v1/` | 2,718 | 266 | 165.0MiB |
| `experiments/strategic-multihero-supply-native-v1/` | 1,476 | 161 | 157.4MiB |
| `experiments/battle-terminal-credit-native-20261023/` | 86 | 21 | 128.3MiB |
| `experiments/strategic-efficiency-reward-v1/` | 94 | 49 | 98.3MiB |
| `experiments/strategic-learned-economy-run-v1/` | 137 | 33 | 96.5MiB |
| `experiments/battle-training-continuation-20261020/` | 64 | 22 | 89.0MiB |
| `experiments/multihero-scheduler-garrison-v4/` | 79 | 21 | 74.9MiB |
| `experiments/ubuntu-native-toolchain-20261025/` | 449 | 47 | 59.9MiB |
| `experiments/human-tactics-v1/` | 144 | 3 | 48.4MiB |
| `experiments/battle-dev-repair-20261023/` | 54 | 10 | 47.1MiB |
| `experiments/human-tactics-events-v3/` | 322 | 27 | 38.0MiB |
| `experiments/strategic-policy-v1/` | 2,095 | 198 | 21.5MiB |
| `experiments/strategic-economy-v4/` | 1,698 | 45 | 13.8MiB |
| `experiments/multihero-mechanism-probe-v2/` | 1,547 | 142 | 12.8MiB |
| `experiments/strategic-threat-response-v1/` | 225 | 30 | 10.8MiB |
| `experiments/strategic-learned-build-exploration-policy-v1/` | 119 | 45 | 6.2MiB |
| `experiments/human-tactics-positive-exchange-v2/` | 97 | 4 | 5.6MiB |
| `experiments/human-tactics-visible-exchange-v1-pilot02/` | 75 | 3 | 5.6MiB |
| `experiments/multihero-scheduler-garrison-v2/` | 161 | 16 | 4.6MiB |
| `experiments/multihero-scheduler-probe-v1/` | 456 | 40 | 4.3MiB |
| `experiments/cpu-simulator-throughput-v1/` | 939 | 323 | 4.1MiB |
| `experiments/battle-opponent-method-review-20261024/` | 17 | 3 | 3.4MiB |
| `experiments/strategic-destination-sampling-calibration-20261024/` | 492 | 43 | 2.9MiB |
| `experiments/strategic-policy-v2/` | 143 | 26 | 2.6MiB |
| `experiments/strategic-learned-economy-native-v2/` | 51 | 15 | 2.4MiB |
| `experiments/expert-mixed-b64-run-v2/` | 21 | 0 | 2.3MiB |
| `experiments/duplicate-stack-audit-01/` | 8 | 1 | 2.3MiB |
| `experiments/strategic-learned-economy-policy-v1/` | 56 | 12 | 2.0MiB |
| `experiments/conservative-ppo-v1/` | 28 | 1 | 1.8MiB |
| `experiments/strategic-active-opponent-learning-20261024/` | 43 | 12 | 1.5MiB |
| `experiments/strategic-server-barrier-readonly-audit/` | 16 | 0 | 1.1MiB |

## Key tracked files

- `README.md` — public project overview and status.
- `BC_INTEGRATION_20261031.md` — training diagnosis and BC feasibility.
- `REPO_EXCLUSIONS.md` — what is not in Git and why.
- `models/MANIFEST.json` — SHA-256 identity index for all local model weights.
- `experiments/strategic-bc-20261031/` — schema6 BC validator/trainer/data contract.
- `NEW_CHAT_HANDOFF_20261023.md` — full goal, authorization and frozen protections.
- `NEW_CHAT_HANDOFF_20261025_UBUNTU.md` — native Ubuntu migration/recovery.
- `NEW_CHAT_HANDOFF_20261026_UBUNTU.md` — latest short handoff.

## Notes

- The counts and sizes above include raw evidence, game data, model weights and
  repaired copies that are **not** tracked by Git.
- `vcmi/` is an upstream checkout; this repository does not relicense it.  Clone
  VCMI separately when reproducing the native environment.
- The repository snapshot filter is described in `REPO_EXCLUSIONS.md`; it is
  intentionally conservative and preserves reports over raw artifacts.
