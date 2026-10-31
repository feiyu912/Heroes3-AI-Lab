# Recovery protocol 01 — terminal-credit native run

Date: 2026-10-23. Status: root-authorized controlled recovery after the
`control-phase-1` resource-gate engineering stop. This is a new reviewed
execution from validated boundaries, not a retry or reseed of the stopped
stage.

## What is being recovered

The old run
`/root/heroes3-ai-lab/evaluations/battle-terminal-credit-native-20261023-01`
completed updates 61, 62 and 63 with official records and audits. It computed
and saved update 64 and its complete raw/target evidence, then stopped in
`post_update_resource()` before recording update 64. The old stage remains
`passed=false` and has no `AUDIT.json`; this protocol does not rewrite that
fact.

`recovery_audit.py` independently rechecks the old stage without modifying it:

- raw prefix/suffix continuity, native returns, legal actions and losses
- exact target reconstruction
- behavior-model and Adam identity during suffix sampling
- update-63 and update-64 CPU restore, counters and complete-boundary metadata
- all 518 embedded frozen inputs
- no writes to the old evaluation directory

Only if that audit passes is `update-64.pt` used as the control starting
boundary. The candidate starts from its already-audited update-62 checkpoint.

## Why this is not a retry

- Control phase 1 is not rerun and its raw native games are not replayed.
- The candidate phase 1 is the first execution of that registered stage, not a
  retry of a candidate stage.
- No seed, curriculum row, model, target rule or optimizer budget is changed.
- The old failed stage and all its files remain untouched.

## Resource-gate correction

The approved plan requires a post-update RAM reserve above 2 GiB. The old
implementation also asserted `swap_used < 256 MiB` after every update, a
stricter condition not stated in the plan's post-update sentence, and its bare
assertion did not record the failing values. In this recovery package:

- the pre-phase guard remains RAM > 4 GiB, swap < 256 MiB, disk > 10 GiB;
- the post-update guard retains RAM > 2 GiB;
- post-update swap use is recorded in every update record but is not a stop
  condition;
- post-update assertion failures include the actual values.

This changes resource bookkeeping only. It does not change the model,
optimizer, PPO samples, targets, native schedule, or scientific factor.

## Registered schedule

1. Recover control update-64 and independently accept it as a starting boundary.
2. Run candidate phase 1 from candidate update-62 to update-64, then audit it.
3. Run control phase 2 (65/66), audit it.
4. Run candidate phase 2 (65/66), audit it.
5. Run control phase 3 (67/68), audit it.
6. Run candidate phase 3 (67/68), audit it.
7. Only after both arms are at update 68, run the pre-registered 96-game DEV
   with parent60, control68 and candidate68.

Each stage is serialized, uses the same single GPU learner and the original
16-worker configuration, and must pass `audit.py` before the next stage.

## Claims

- The recovery audit is not an ability result.
- Training wins, checkpoint validity and optimizer counts are separate claims.
- The 96-game DEV is the pre-registered independent comparison; small-sample
  results must not be reported as a population win rate or automatic
  promotion.
- No final-test data is used.
