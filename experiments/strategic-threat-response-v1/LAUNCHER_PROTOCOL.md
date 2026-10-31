# Review-only two-stage launcher

run_phase_a.py defaults to prepare-only: it inventories/fixes the model, code, native source/runtime, config and training maps; searches seed-bearing JSON indexes; writes a new plan/source snapshot; and starts no subprocess or game, reserves no pool and imports no torch. `--help`/import also cannot run anything. Source files elsewhere remain untouched. Explicit game execution is reserved for root's later release of the shared pool.

The trained model is now fixed in code to strategic-vector-v1/native-cuda-boundary-clean-4env-01/continuous-2/update-2.pt, SHA256 `9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159`, in both arms. This resolves the old model-selection placeholder before any arm runs; it does not pick an arm-specific model or claim the recent dev net-zero result was an improvement. All16 games are NK on the original training map/role/seed1881/82 jobs. The current checkpoint is loaded by CPU argmax broker, no optimizer.

The two stages are separate invocations. Baseline requires exact original reviewed native source and the runtime frozen at prepare. It runs all8 episodes into fresh baseline/00..07 directories. Only a completed8-row independently audited baseline can unlock the candidate command. The launcher never patches, installs, compiles, restarts or selects a native variant. Root must independently preserve the original variant and install/build candidate after no running worker uses it.

Candidate stage requires exact reviewed candidate source, exactly the same complete native source set, all other sources unchanged (including all three explicit server barrier source SHA), unchanged shared runtime/model/config/runner inputs, and an explicit compiled-binary attestation JSON. Its format is `{candidate_source_sha256: <reviewed candidate SHA>, binaries: {<absolute binary/module path>: <SHA>}}`. The binaries dictionary must equal a fresh `run_phase_a.binaries()` inventory, and at least one runtime binary must differ from baseline; source-only installation with stale identical binaries is rejected. Source/runtime checks happen before a new candidate arm is created, and all hashes are checked before and after each episode. The attestation itself is frozen during the stage. Candidate source edits cannot be hidden by rebinding it to another hash.

Each arm refuses existing output directories. Native failures stop and retain failed status/evidence; no loss is imputed and no pair is deleted. The runner owns the shared pool lock and natural120second game deadline; pool waiting is not counted as game time. SIGINT/SIGTERM abort through owned-descendant cleanup and leave a failed record. No GPU device is exposed to the broker subprocess.

Per-episode audit combines the existing new-policy exact model/IO/native MoveHero verifier with the conserved-supply/hero-loss raw audit, full rejection/query service scan and exactly-one-terminal rule. Only native_battle_ready can follow terminal, with all other fields identically serialized; before_move, release, ACK, unknown events and state/type changes are rejected. Each threat_commit_released is matched to a real prior commit in that own turn, the following real native decision and the same visible-pressure gate; it does not substitute for action confirmation. Direction reversals and within-turn target switches are counted. Archived baseline logs, trace, decision, broker, request and action hashes remain immutable across candidate installation. Final results show each fixed pair and net win difference, with two-map clustering/no strength certification made explicit.

CPU tests cover wrong source/server deltas, added source files, stale binary attestations, seed collisions, altered frozen inputs and terminal-tail counterexamples. These tests do not certify C++ compilation, native game behavior or strategic benefit.

Future commands (not run here), using the existing CPU interpreter:

```
python run_phase_a.py --out <new-root>
python run_phase_a.py --out <prepared-root> --stage baseline --execute
# Root preserves baseline variant, installs/builds exact candidate, freezes build attestation.
python run_phase_a.py --out <prepared-root> --stage candidate --execute --candidate-build-manifest <attestation.json>
```

The earlier PHASE_A_BINDING_TEMPLATE.json is a nonexecuting design template and stays unchanged. The actual prepared plan fixes the trained checkpoint and all current inputs; candidate binary attestation is intentionally available only after the staged compile boundary.

pilot01 stopped at the fifth native-complete game because the old raw auditor overwrote duplicate creature slots. Its failed stage and source snapshot are preserved. pilot02 is an explicit full eight-game engineering repeat using `--repeat-validation-of <pilot01>` during preparation; it binds the old plan SHA and exact jobs/checkpoint, and only permits already used seed-index entries under that original failed batch's outputs/native/agent directories. Other collisions still stop. Audit v3-stack-sum aggregates every creature slot, backed by11 duplicate/split/merge/conservation counterexamples. No native, model, threshold or candidate behavior changes. These reruns are repeated engineering validation and are not added as new independent capability samples. Old training history is not rewritten: the PPO collector does not use this Counter helper.
