# Repository exclusions and sensitive-data policy

The lab directory is ~24 GiB.  A public Git repository must not contain the raw
native evidence tree, copyrighted game assets, model weights or unrelated
personal material.  This repository therefore tracks **source, plans, reports,
manifests and audit summaries**.  The full on-disk structure is described in
`PROJECT_STRUCTURE.md`.

## Explicitly excluded

| Path / pattern | Why | Where it remains |
|---|---|---|
| `.research/` | unrelated personal research/job material | local only |
| `vcmi/` | upstream VCMI checkout, separate GPL repository | clone `https://github.com/vcmi/vcmi.git` |
| `models/**/*.pt`, `*.pth`, `*.onnx` | model weights; 1.1 GiB in the lab | `models/MANIFEST.json` records identity |
| `**/*.vmap`, `*.vsgm1`, `*.sav` | Heroes III maps/saves, copyrighted game data | local lab profile |
| `**/Data/`, `**/Mods/`, game assets | copyrighted game data / large assets | local lab profile |
| `experiments/**/native/`, `agent/`, `runs/`, `data/`, `config/`, `cache/` | generated native run trees and copied config | original run directory |
| `experiments/**/frozen-inputs/`, `archive/`, `delivery-*/`, `evidence-package-*/` | duplicated frozen inputs/raw evidence; huge | original experiment directory |
| `experiments/**/native-evidence-*/`, `capsule-evidence-*/`, `build-evidence-*/`, `source-snapshot/` | raw capsule/native evidence and binaries | original experiment directory |
| `experiments/ubuntu-native-takeover-20261025/verified-repair/` | 3.3 GiB repaired filesystem copy | local recovery archive |
| `experiments/ubuntu-native-takeover-20261025/evidence-review/` | 1.1 GiB audit/history archives | local recovery archive |
| `experiments/ubuntu-native-takeover-20261025/restored-history/` | 210 MiB restored history | local recovery archive |
| `research/downloads/` | 95 MiB wheels/debs; reproducible | local cache |
| `**/*.log`, `**/*.jsonl` | huge raw logs / line-delimited evidence | original run directory |
| `**/*.tar*`, `*.zst`, `*.gz`, `*.zip`, `*.whl`, `*.deb` | archives/packages | original run directory |
| `**/__pycache__/`, `*.pyc` | generated | reproducible |
| `handoff/` | local handoff copies; not needed publicly | local only |

## What is included

- all top-level handoff/goal/analysis documents;
- `research/*.py`, `*.md` and small report JSON;
- `experiments/**/*.py`, `*.cpp`, `*.h`, `*.md`, small `RESULT.json` /
  `AUDIT.json` / `PLAN.json` summaries where they are below the size thresholds;
- the new `experiments/strategic-bc-20261031/` validator/trainer and data contract;
- `models/MANIFEST.json` and `models/README.md` (no weights);
- `PROJECT_STRUCTURE.md`, `README.md`, `BC_INTEGRATION_20261031.md` and this policy.

The staging filter used for the 2026-10-31 snapshot:

- JSON files > 50 KiB are not uploaded (large raw audits remain local);
- text/source files > 1 MiB are not uploaded;
- files without a source/documentation extension must be ≤ 200 KiB and are
  normally excluded when they look like binaries;
- symlinks are not staged (the lab has many links to game data, maps and
  frozen binaries; some are intentionally dangling).

## Sensitive data

The source tree was scanned for API keys, tokens, passwords, private keys,
cloud credentials, `.env` files, browser profiles and SSH keys.  No such
credentials are included.  The following are also deliberately absent:

- `~/.codex/` (conversation/auth state),
- Codex session rollouts and attachments,
- HOME-directory paths with user-private content (some historical reports still
  contain lab paths for reproducibility; these are not credentials),
- any game video/audio or full transcript.

If a historical report contains a local absolute path, treat it as provenance,
not as a public endpoint.  Do not add tokens, cookies, SSH keys or personal
data to issues or commits.

## Restoring excluded artifacts

The authoritative copies are on the native Ubuntu profile and the repaired
backup, described in:

- `NEW_CHAT_HANDOFF_20261025_UBUNTU.md`
- `experiments/ubuntu-native-takeover-20261025/REPORT.md`
- `experiments/ubuntu-native-takeover-20261025/evidence-review/RECOVERY_METHOD.md`

The `models/MANIFEST.json` file lets you verify a restored weight by SHA-256.
Experiment reports name the exact raw artifact paths and hashes.  Do not
reconstruct a missing artifact from a summary and call it original evidence.
