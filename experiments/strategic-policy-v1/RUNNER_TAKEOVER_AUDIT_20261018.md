# Runtime, replay and timeout audit (2026-10-18)

This audit did not start a game or GPU learner. The parent agent ran the exact replay; this branch read its evidence and implemented the replay/runner support.

## Runtime integrity

`TAKEOVER_RUNTIME_AUDIT_20261018.json` records a nonblocking lock probe during the parent's replay: pool held, GPU learner lock free. Only replay and its isolated client appeared. The five frozen battle files and B64/update-1/update-2 checkpoint SHA256 values match the handoff. GPU usage at that instant is incidental, not evidence of training.

## Exact replay and fog evidence

The parent replayed all 11823 original policy responses. The broker verifies every original raw request file against the stored SHA and parsed rollout request before launching the runner. New requests must equal original requests after removing only `request_id`; any divergence stops responses. Replay outputs are always `valid=false`, `winner=null`, diagnostic only. This is neither evaluation nor an optimizer update.

`REPLAY_FOG_AUDIT_02.json` is reproducible with `audit_replay_fog.py RUN_DIR ORIGINAL_ROLLOUT NEW_OUTPUT`:

- Native first packets: 11819 SUCCESS, 4 BLOCKING_VISIT; the old 11823 changed reply coordinates overstated true displacement by 4. Adjacent rollout origins show 11818 actual changes and 4 unchanged origins; the final move has no subsequent request origin.
- Only 214 of 11823 moves reveal new tiles. Native reveal union covers 963 tiles, none of the nonempty first packets is entirely repeated. No frontier candidate has all neighbors already present in the prior reveal union. Enemy hero tile `(29,10,0)` is never included in a reveal packet. These observations do not show missing/reverted fog updates.
- 11803 selected goals are beyond the next step; 11569 of those switch destination on the next policy request. This strongly supports per-step goal switching as a contributor to slow exploration, without proving that it is the only cause.
- Resource `(26,15,0)` is not repeatedly collected: replay client log lines 858625–858726 show its eventual final visit, BLOCKING_VISIT, resource grant and RemoveObject id10 applied in server/client. Earlier repetitions are remote target choices, not completed visits.

The parent additionally observed native target diagnostics `info_unavailable` for the partly visible enemy hero and `no_current_turn_path` for the enemy town. More exact path node/end-action diagnostics are needed before choosing a behavioral repair. No hidden-state access is justified by the hero's partial sprite visibility.

## Runner changes and verification

`adventure_runner_v5.py` now cleans the isolated client process group on normal exit, timeout, SIGTERM and SIGINT before releasing the simulation lock. A stubborn TERM-ignoring synthetic child was removed; the synthetic pool lock was held before interruption and free afterward, with interrupted/incomplete result. See `RUNNER_CLEANUP_SYNTHETIC_20261018.json`. This fake-engine check ran entirely in `/tmp` and did not use the real simulation pool or GPU. Its first snapshot predates the cosmetic correction that separates interruption from crash.

The runner additionally reports target trace SHA/count, native last calendar day, native-calendar fallback for an otherwise missing turns field, displacement reply count excluding blocking visits, and a note on the legacy changed-coordinate field. SIGKILL of the runner itself still cannot execute Python cleanup; external supervision is needed for that case. Descendants escaping the client process group are not covered by this change.

The replay's decision boundary stops after committing its final response; response count is not a substitute for post-run native consumption verification. Its day boundary is observed on policy requests, so silent native turns still rely on runner timeout. All these boundaries are invalid diagnostic truncations, never assigned wins/losses.
