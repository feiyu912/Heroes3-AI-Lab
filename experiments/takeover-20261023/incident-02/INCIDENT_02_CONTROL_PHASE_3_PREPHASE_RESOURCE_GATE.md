# Incident 02 — control-phase-3 pre-phase resource gate

Date: 2026-10-23. Status: engineering stop. No automatic retry, no reseed, no
training update started.

## Trigger

The recovery-01 controller (`battle-terminal-credit-recovery-20261023-01`)
exited 1 at `control-phase-3`. The stage directory contains:

- `RESULT.json`: `passed=false`, `records=[]`, `actual_Adam_steps=8448`,
  `checkpoint=.../control-phase-2/update-66.pt`, `error="AssertionError()"`,
  `partial_native_not_restorable=true`;
- `RESTORATION.json`: model/optimizer restore happened before the resource gate;
- no `PROGRESS.json`, no `phase-3/` directory, no update 67 or 68.

The stage log traceback is at `learner_impl.py:25` in the **pre-phase**
`resource()` assertion, not in a training update, native worker, target
construction, or audit.

## Resource evidence

`candidate-phase-2` was the last completed stage. Its final record (update 66)
reported:

- `available_mib = 6064.26171875`
- `swap_used_mib = 309.3046875`

The pre-phase guard requires all of:

- `MemAvailable > 4 GiB`;
- `swap used < 256 MiB`;
- `disk free > 10 GiB`.

The only observed threshold exceedance immediately before the stop is swap:
`309.3046875 > 256 MiB`. After the controller exited, the host reported swap
`0 MiB`, `MemAvailable` about `15.2 GiB`, and root disk free about `793 GiB`.
The old bare assertion did not record which term failed, so the diagnosis is
strongly supported by the stage sequence but not proven term-by-term. This is
why recovery-02 adds complete pre-stage value logging; it does not lower any
threshold.

## What did not happen

- No phase-3 native game was played.
- No phase-3 target was built.
- No optimizer step, checkpoint, DEV game, or final-test game was produced.
- Recovery-01's completed stage 1/2 evidence and audits were not modified.
- No seed was changed and no stage was retried.

## Recovery-02 decision

Start from the validated update-66 boundaries of both arms:

- control: `control-phase-2/update-66.pt`, SHA
  `90347e729ae36be8e050fdbcf1cb5973e19ece1fc18374152d2772d0f72e4fb3`;
- candidate: `candidate-phase-2/update-66.pt`, SHA
  `987d85e50f988267d257c064c856b2da1bb05672c4fce3499720656ea87b1105`.

Before each remaining phase, wait up to 180 s for swap to fall below 256 MiB,
recording the initial value, every sample, and the final value. The existing
pre-phase thresholds remain unchanged. If swap does not drain, stop again with
the values preserved. Then run control/candidate phase 3 and, only after both
update-68 checkpoints pass audit, the pre-registered 96-game DEV.

This is another reviewed recovery from a complete boundary, not a replay of
control-phase-1/2 and not a retry of the failed pre-phase check.
