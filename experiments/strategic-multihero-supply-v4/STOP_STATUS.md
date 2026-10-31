# User-requested stop — 2026-10-19

V4 is **unfinished, not frozen, not native-built, not native-qualified and not restore-qualified**. Stop requested by root following the user's explicit instruction. No further implementation, CPU testing, shared compilation, native execution or GPU work will be performed until resumed.

## Current changes

- Frozen supply-v3 was copied into the separate supply-v4 directory. V1/v2/v3 files were not edited.
- Added `SupplyRecovery.h`: pure C++ SHA256 and strict versioned full control/owned-world codec. Includes controller roles/turn/budgets/blocked/goals, visited, reserve/cargo slot contributions, all job ledgers, owned heroes/towns and an owned economy snapshot.
- Added `SupplyRecovery.inc`: proposed explicit playerLocalSettings namespace persistence through actual SaveLocalState ACK, then actual SaveGame ACK; checkpoint events; native-payload hydration and first resumed-yourTurn handling without beginTurn increment/reset. Current design has no release wait or polling thread: reference continues after Save ACK.
- Replaced v4 `prepare.py`: derives thirteen candidate inputs from frozen v3, adds recovery hooks and a Client load gate, embeds a source token with a normalized hash to avoid self-reference, and extends the builder's exact five-file deletion whitelist. Client gate was narrowed to supply/recovery/native-marker loads to preserve old typed loads. Own local-settings reads now use const JsonNode references to avoid inserting null keys into old typed state.
- Added `test_recovery.cpp` and an isolated two-translation-unit syntax checker.
- Added `recovery_bundle.py`: proposed Python decoder, actual event/ACK/save-success-marker gates, stable native-save header/SHA checks and atomic native-save/bundle publication. **This new helper has not been run or syntax-tested.**

## Last actual checks (not current-source certification)

- The standalone synthetic C++ recovery codec/SHA test passed **31 checks**, including nontrivial cargo/budget/cursor/navigation roundtrip and rejected corrupt state. This was before some later source edits; no native claim.
- Isolated actual Director and Client translation-unit syntax checks both passed at the then-generated source token `8bf43fd2ed69367a411d74bbf0b7b3bd152d9d6c63890c429900e0826cce1049`. No objects, shared build outputs or game processes were produced.
- Since those checks, additional decoder guards, owned-ACK resume handling, const local-settings reads, per-own-turn checkpoint events and the Python bundle helper were edited. They have **not** been retested or regenerated into the candidate.
- The copied v3 CPU/trace reports and earlier plan directories in this directory are inherited history. They do not certify v4.

## Incomplete work and concrete risks

1. `candidate/`, its source token/manifests and NATIVE_SYNTAX.json are currently stale relative to the latest templates. Do not build or run this candidate as frozen input.
2. The Python helper needs real tests, independent decoder/C++ crosschecks, failure fixtures and atomic-publication verification. No actual native bundle has been created here.
3. Existing copied v3 `check_cpu.py`, trace tests and README have not been adapted to the v4 manifest/recovery changes. A dedicated v4 report is still required.
4. Independent reviewer requested structured actual boundary flags in recovery events: pending strategy, movement/battle, native query/replies, deferred turn, turn_active/ending_turn and logical owned requests. These additions are **not implemented**. Explicit Save pack type/payload observations were also suggested.
5. Root's separate boundary runner and the independent checkpoint auditor still need interface review against the helper/event schema. No reference-vs-fresh native continuation comparison exists.
6. SaveGame ACK success alone is insufficient: the server save implementation catches file-write failure while its visitor returns success. Require a successful-save marker, a fresh stable actual .vsgm1, native header/SHA and subsequent actual fresh load.
7. SaveLocalState mutates server settings; the current client's cached settings need not reflect that write. Fresh native load is the intended source for hydration, never external sidecar values.
8. Native hydration, source/save/world gates, late interface-ready ACK ordering, omission/disabled-mode rejection, preservation of legacy typed loads and exact accepted-source/binary restoration all remain unverified at runtime.

## Resume entry points

Read this file, v4 templates, root's `experiments/strategic-supply-boundary-native-v4/PLAN.md` / `run_native_boundary_v4.py`, and the independent `experiments/strategic-supply-checkpoint-audit-v1` review before proceeding. Root controls native/shared build execution. Do not change frozen v3.

After explicit resume, complete review fixes and CPU tests first; then run the v4 `prepare.py` to regenerate all thirteen candidate inputs and source token, rerun both isolated syntax checks, generate a new plan-only build output, and announce a new exact freeze to root. Do not reuse the stale manifests/token above as final.

## Activity at stop

This agent has no outstanding tool session, own compiler process, native game, GPU task or resource lock. The last syntax and standalone CPU invocations already returned. This statement concerns this agent's work; root coordinates any other activity.
