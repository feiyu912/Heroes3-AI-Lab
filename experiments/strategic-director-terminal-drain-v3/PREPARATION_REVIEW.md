# Closed-registry terminal drain v3: prepared and CPU checked

This directory preserves all v2 inputs separately. Preparation changed only `candidate/client/Client.h` among the nine native payloads. It did not install source, build the VCMI engine, run a game or use the GPU. `CANDIDATE_MANIFEST.json` and `candidate.diff` describe the new review candidate; `PREPARATION.json` records exact source/plan/diff/manifest SHA before any root-controlled build.

The existing atomic termination remains: under the vector mutex, set terminating, copy actual pending IDs, clear, notify and return those cleared IDs. Three additional class changes address operations racing with that boundary:

- `pushBack` acquires the mutex before checking the terminating flag and throws `TerminationRequestedException` instead of relying on a lock-external assertion.
- `waitWhileContains` includes the terminating flag in its condition predicate, then throws the existing exception.
- `tryRemovingElement` acquires the mutex and returns false after termination, allowing a late foreign ACK without asserting.

The existing `requestTermination` method is retained. This does not synthesize a native request, ACK, success, policy transition or reward. A Director request that appears after the owned-drain boundary still fails the strict ledger audit; this patch is not a promise that every other client lifecycle race is solved.

## CPU evidence

`threaded-cpu-01/AUDIT.json` passes 138 checks on the **actual extracted candidate class**, compiled unchanged with g++17/pthread. Standard-library `vstd`/exception support shims stand in for engine includes. There are 30 producer-versus-termination races and 100 ACK-versus-termination races; every accepted push is present in the atomic cleared set, later pushes throw, waiters unblock, late ACK removals return false, and the old termination entry point remains usable. This run accepted2932 pushes and rejected4748 late pushes. These counts are scheduling-dependent CPU observations, not game throughput or a native execution certificate.

`cpu-audit-01/AUDIT.json` additionally passes 28 malformed/tampered registry/proof cases and five whole-game negative cases. This includes the newly mandatory unconditional actual ACK for every Director-specific ACK, wrong packet type, missing registration, cancellation containing an owned ID, an unexplained foreign snapshot difference, an old registry epoch and a valid event prefix with killed exit−15. Fixtures are artificial and explicitly `real_execution_certified=false`.

All nine Python files parse, the new runner's help path loads, and the complete preparation source SHA record verifies. No frozen v1/v2 file or historical game artifact was changed.

## Binding and next root-controlled checks

The explicit epoch is `atomic-termination-closed-registry-v3`. Runner and v6 independently require all nine manifest hashes to match the actual capsule's compiled `build-source-manifest.json`, immutable `source-snapshot`, and build attestation. The game PLAN freezes the candidate manifest, all nine payloads, compiled source manifest and the original proxy/model/script inputs. A reused v1/v2 marker cannot certify this atomic epoch. The v3 replan auditor requires v6's compiled-epoch proof and current exact auditor/registry source SHA.

`qualify.py` targets `typed-director-terminal-drain-capsule-03`. Root must first build under the existing resource locks and restore accepted source/binaries exactly; then perform the unchanged hang-seed and red/blue Empty engineering qualification. Native success, process exit0, policy request/actual application/ACK equality and foreign cancellation proof remain unverified at preparation time. Original failed runs remain invalid/unscored.
