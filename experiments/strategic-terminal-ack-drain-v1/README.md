# Headless terminal ACK drain

Observed failure: typed runtime `cell-02`/seed2026102812 loses after7 days without a town. Actual EndTurn330 succeeded server-side, but its PlayerEndsGame packets arrived before the final PackageApplied. The original headless client immediately shut down, losing the ACK. The strict episode gate rejected it; no failed curriculum was updated.

This isolated source epoch adds only a mutex-protected `ThreadSafeVector::empty()` and defers testmap/testsave automatic shutdown until the existing `CClient.waitingRequest` is empty. `visitPackageApplied` still delivers the real callback and removes the real request before checking shutdown. Server apply/ACK behavior, game rules and outcome are unchanged; nothing fabricates a completion. Interactive UI behavior is unchanged. Unreceived ACKs still lead to the external engineering timeout and invalid data, not a win/loss substitute.

Real build capsule `/root/heroes3-ai-lab/evaluations/typed-schema4-ack-drain-capsule-01/EXECUTION.json` passed. After building, the accepted V8 source/header and three runtime files were restored and recompiled to exact original SHA. New capsule client SHA332e985b…, implementation lib remains9c33166b… (same typed game logic as before the lifecycle fix). The original frozen battle environment was never modified.

`regression-exact-01/AUDIT.json`: same seed, checkpoint,100 requests/responses and four gameplay/policy traces byte-for-byte. Real EndTurn330 ACK now observed after game_over, no native action after terminal, unchanged red defeat day12. `native-repro-raw-audit-01` passes all110 actual action applies/ACKs. `admitted-repro-01` exactly replays the100 CUDA sampled policy choices; this duplicate regression is not a second independent capability sample and is excluded from the new logical-update0 curriculum.

The new source/runtime fingerprint requires explicit weights initialization for a new training protocol; old optimizer continuation is not disguised as same-protocol resume. The fixed capsule remains isolated. These are transport and lifecycle results, not a strategic strength improvement.
