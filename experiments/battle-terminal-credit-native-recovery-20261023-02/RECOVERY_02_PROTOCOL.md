# Recovery protocol 02 — terminal-credit phase 3 continuation

Date: 2026-10-23. Status: reviewed continuation after the recovery-01
`control-phase-3` pre-phase engineering stop. Root has asked to continue; this
protocol preserves all previous evidence and does not lower a resource
threshold.

## Exact starting point

Recovery-01 completed and independently audited:

- candidate phase 1 (updates 63/64);
- control phase 2 (updates 65/66);
- candidate phase 2 (updates 65/66).

Both arms are at update 66, Adam 8448. The starting checkpoints are:

- control:
  `/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-01/control-phase-2/update-66.pt`
  SHA `90347e729ae36be8e050fdbcf1cb5973e19ece1fc18374152d2772d0f72e4fb3`;
- candidate:
  `/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-01/candidate-phase-2/update-66.pt`
  SHA `987d85e50f988267d257c064c856b2da1bb05672c4fce3499720656ea87b1105`.

`control-phase-3` did not start a native phase. It has no progress file and no
update. It is preserved as a failed engineering stop, not reinterpreted as a
training result.

## Resource handling

The failed pre-phase assertion had three terms and did not log values. The last
completed stage ended with swap `309.3046875 MiB`; after process exit swap was
`0 MiB`, while RAM and disk were ample. Recovery-02 therefore adds a
**pre-stage readiness wait** outside the frozen training package:

- thresholds are unchanged: RAM > 4 GiB, swap < 256 MiB, disk > 10 GiB;
- before each remaining stage, poll at most every 5 s for up to 180 s;
- write `WAIT-<stage>.json` with initial/final values and all samples;
- start the stage only after the same thresholds pass;
- if the wait expires, stop and preserve evidence; do not lower the threshold.

The frozen recovery-01 `learner_impl.py` is reused unchanged. Its own pre-phase
guard remains the final authority and still stops the stage if the condition
changes after the wait. The post-update RAM > 2 GiB guard remains; post-update
swap remains recorded rather than a stop condition, as in recovery-01.

## Schedule

1. Read-only boundary audit of recovery-01 control/candidate phase-2 and
   update-66 checkpoints.
2. Wait for the pre-stage gate; run control phase 3 (updates 67/68); audit.
3. Wait for the pre-stage gate; run candidate phase 3 (updates 67/68); audit.
4. Only after both update-68 checkpoints pass audit, run the pre-registered
   96-game DEV with parent60, control68 and candidate68.
5. Run the independent DEV raw audit and full CPU replay.

No phase 1 or 2 stage is replayed. No seed is changed. No training row is
regenerated. The recovery-01 package and evaluation directory are read-only
inputs.

## Claims

- Recovery-02 is an engineering continuation, not evidence of a stronger policy.
- Update-68 validity, training wins and DEV outcomes are separate claims.
- The 96-game DEV is a small pre-registered sample. It must not be reported as a
  population win rate, a 95% claim, or automatic promotion.
- No final-test data is used.
