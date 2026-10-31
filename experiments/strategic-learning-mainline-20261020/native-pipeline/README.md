# Training mainline native integration — 2026-10-20

Minimal Python adapters for the already qualified `typed-director-terminal-drain-capsule-03`. Native source, binaries, the existing v4 auditor, frozen schema4 encoder/model and the original sampler/PPO implementations are unchanged. Transport v4 remains shelved.

Runtime entries are frozen: `collect_episode_v5.py`, `admit_episode_v5.py`, `train_update_v3.py`, `pipeline_common.py`, `run_pipeline.py`. The three `.diff` files show changes against the original typed-training-v1 entries. Preparation scripts regenerate adapters and must not be run while an experiment is active.

Collector changes are limited to qualified-capsule provenance, complete source/helper/artifact freezing, the Director terminal marker, and explicit Director/atomic-registry/audit metadata. All nine candidate payloads bind to the compiled source snapshot and attestation; all capsule artifacts are frozen. Runtime Lua assets retain the original full-source-manifest check. New training cells cannot use a loaded save or scripted transport mode.

Admission invokes the original exact CUDA replay. Its entire replay block is byte-identical to typed-training-v1/admit_episode_v5.py: action, log probability, value, response, model/request digest, initial RNG and final RNG must match exactly. Native auditing uses the unmodified strategic-director-terminal-drain-v4/audit_game_v6.py. Its exact three source keys resolve to that directory's audit_game_v6.py and director_registry_v1.py, plus strategic-typed-native-v1/raw_events_v4.py. Untagged legacy re-audits are not admitted into this epoch.

Training imports the unchanged episode_balanced_ppo, model_io and load_admitted modules. It keeps terminal win/loss rewards and the original PPO calculation/settings. Its source/protocol identity explicitly includes the new collector/admission and qualified auditor. Exactly eight distinct complete episodes must cover the two Training maps, both roles and EmptyAI/Nullkiller2, with one parent checkpoint and logical update. Partial, duplicate-cell or mixed-policy curricula cannot update.

The first batch is pinned to the supplied temperature2 initialization SHA `d5908330038444107ed9ba00585fb068e453a5d1636856ba994d9aa3eb68df72`. `run_pipeline.py` passes `--initialize`, explicitly creating a fresh Adam optimizer in the new protocol epoch. It does not claim continuation of the old Adam state. Seeds are 2026102000 through 2026102007 in map/opponent/role order. No extra reward or policy method is introduced by these adapters.

Default execution is plan-only:

```text
python run_pipeline.py --out <new-plan-directory>
```

Root may run the same command with `--execute`; `--collect-only` gathers/admit all eight cells without an optimizer update. Each cell executes collection, the original native auditor and exact CUDA admission in sequence. After eight admitted cells, the original PPO update runs once through the new source-bound entry. The original audit_checkpoint_cuda.py remains available for the delivered checkpoint. Existing failed evidence and partial-update files are retained.

`plan-01/PLAN.json` is the CPU-prepared plan. `CPU_REPORT.json` records 24 CPU checks: syntax, exact unchanged replay/PPO source checks, actual capsule/initialization hashes, and explicitly synthetic metadata/curriculum rejection cases. These are not native or CUDA training certification. This agent performed zero native runs, CUDA inference or optimizer steps. Root separately started the actual run in `/root/heroes3-ai-lab/evaluations/strategic-mainline-temperature2-train-01`; its eventual raw/admission/training results are authoritative.

No input is to be hot-edited during that run. Any discovered defect requires a new frozen epoch after the current run stops. Training outcomes are not independent evaluation or evidence of improved playing strength.
