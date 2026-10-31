# Incident 01 — control-phase-1 post-update resource gate

Date: 2026-10-23  
Status: **ENGINEERING STOP**. No retry, no reseed, no automatic recovery,
no ability promotion, and no DEV/final-test result.

## Summary

The pre-registered terminal-credit native run stopped in `control-phase-1`
after update 64 had been computed and saved, when `post_update_resource()`
raised a bare `AssertionError`. The controller therefore stopped before
`candidate-phase-1` started. This is a resource/engineering stop, not a game
loss, not a target-eligibility failure, and not evidence that the candidate
factor does or does not improve play.

The stopped stage left a complete-looking update-64 checkpoint and all raw
native evidence, but no update-64 record and no official `AUDIT.json`. A
separate read-only post-incident check reproduced the raw prefix/suffix and
target evidence and restored both update-63 and update-64 learner boundaries
successfully. That check is *not* a stage acceptance and does not authorize
resumption.

## Stages that completed before the stop

| Stage | Result | Adam total | Updates | Checkpoint / audit |
|---|---|---:|---|---|
| `qualification` | passed | 7680 | none | 2,048 native rows; 0 optimizer steps; independent audit passed |
| `control-micro` | passed | 7936 | 61, 62 | update-62 SHA `d2b3b9aec6ba19bc55654a5f22af0cf59530ff30ffdeec0372bd6cf34357426a`; audit passed |
| `candidate-micro` | passed | 7936 | 61, 62 | update-62 SHA `4d61809c0bd208dcc09071aa760444002f5b2c1dd25b9e945cfbc1e527e2b5d5`; audit passed |
| `control-phase-1` | **failed** | 8192 | 63 recorded; 64 unrecorded | update-63 SHA `6d0a90c70ec642f31c0535f40c3d1977efc32c6c3667b28c8e86edbeddafa1ec`; update-64 SHA `4ef6e7e27ffcc56f7b261a55c52e38505be24a162f8196d2ccd3a60be734cb59`; no audit |
| `candidate-phase-1` | never started | — | — | — |

The two micro stages each used 256 new Adam calls and both passed independent
audit. The paired schedule is now broken: control is at update 64, candidate is
at update 62.

## Exact failure site

`experiments/battle-terminal-credit-native-20261023/learner_impl.py`:

```python
def post_update_resource():
    ...
    assert m['MemAvailable']>2*1024*1024 and m['SwapTotal']-m['SwapFree']<256*1024
```

The traceback is at `learner_impl.py:30`. The failing function checks two
conditions:

- `MemAvailable > 2 GiB`
- `swap_used < 256 MiB`

The code had already completed, written, and read back `update-64.pt` before
calling this guard. The subsequent record append and `PROGRESS.json` write
therefore did not occur. `control-phase-1/RESULT.json` contains only update 63
and reports `error: "AssertionError()"` and
`partial_native_not_restorable: true`. The controller then reported:

```text
AssertionError('control-phase-1 failed: preserve evidence, no retry')
```

### Which resource condition failed?

The assertion does not log the update-64 values, so the exact clause cannot be
reconstructed from the preserved evidence. The last recorded row (update 63)
had:

```json
{"available_mib": 7067.80078125, "swap_used_mib": 184.578125,
 "gpu_temperature": 41.0, "gpu_memory_mib": 2136.0}
```

The preceding micro rows had swap usage `0.0` (control update 61),
`0.0` (control update 62), and `1.51171875` (candidate update 62). At update 63
the swap value was already only 71.42 MiB below the 256 MiB threshold, while
`MemAvailable` was 5,019.8 MiB above its threshold. After shutdown the system
shows `MemAvailable=15059.1 MiB`, `SwapUsed=0.0 MiB`, no learner/worker
processes, no held locks, and GPU 48 °C / 1,219 MiB.

**The swap condition is therefore the only near-threshold candidate, but it is
not proven.** The honest conclusion is: failure of the two-clause post-update
resource guard, with swap the strongly indicated clause. The bare assertion is
an evidence gap in the implementation.

The approved plan requires a post-update `>2 GiB` reserve but explicitly lists
`swap<256 MiB` only for the pre-phase check. The implementation also enforces
`swap<256 MiB` after every update. If the failed clause was swap, the stop was
caused by an implementation gate stricter than the plan's post-update sentence,
not by a failure of the model, targets, or native game. This discrepancy needs
review before any recovery; it must not be bypassed silently.

## Preserved evidence

Evaluation directory:
`/root/heroes3-ai-lab/evaluations/battle-terminal-credit-native-20261023-01`

Key files:

| File | SHA-256 |
|---|---|
| controller `RESULT.json` | `edc6f3034a16e411dd3c48928ff9330cd9645c2bcffdfc81c977c3588c259ce8` |
| controller `RESULT.partial.json` | `693df5b1a9089cf39630a71f4c8fcd3baf3ce3576868a5122d4c30e57d0dad3c` |
| `control-phase-1/RESULT.json` | `a65f333506db8a9b5dfad993eafdc8ae45f3d04c408a59902f17b2d79d87478f` |
| `control-phase-1/PROGRESS.json` | `7c64f79834441a7596ba81dfc1c3a8bb12d4f65acfb6e3c8a5880499065cf1df` |
| `control-phase-1.log` | `aac79d9e21b14131e6d51c33228eafc61e622d537e20c20b20d4e32183196152` |
| `control-phase-1/update-64.pt` | `4ef6e7e27ffcc56f7b261a55c52e38505be24a162f8196d2ccd3a60be734cb59` |
| `control-phase-1/phase-1/TARGETS.pt` | `029ab191077d9e4f3ef42f90b93d6c690daa3c452edc88ac2286f6e49a21e636` |
| `control-micro/RESULT.json` | `590103b8b81136f487ad2d61901e8a79e86e45b9cf831a89f9ceea03a8125c03` |
| `candidate-micro/RESULT.json` | `c86093c34894b65358980968a990f7c77c9e28ca84d1ebfcb3f721081f2fc81e` |

`control-phase-1` contains 267 files and 2,003,972,210 bytes, including 128
decision files, 128 return files, 256 journal files, prefix/suffix evidence,
`TARGETS.pt`, and the two update checkpoints. No file was deleted or rewritten.

## Read-only post-incident validation

Script:
`experiments/takeover-20261023/post_incident_check_01.py`

Output:
`experiments/takeover-20261023/incident-01/POST_INCIDENT_CHECK.json`
(SHA-256 `61780cb8bfb94eeeb95c7eea74b01c317608c60f2551755b6ad8e74957812a8f`)

The script used only the CPU, did not start native workers, did not run an
optimizer, and did not write into the evaluation stage. Results:

- Raw evidence and target reconstruction passed:
  - 1,024 admitted prefix rows and 1,024 suffix rows
  - 256 journal files
  - 35 prefix terminations and 39 suffix terminations
  - 14 of 16 workers eligible (`real_terminal_extension`); two were
    `prefix_already_ended`
  - recomputed `targets.build` arrays are exactly equal to the saved targets
  - saved suffix evidence has the behavior model and Adam digests of update 63
- Both learner boundaries restore exactly:
  - update 63: `completed_updates=63`, `environment_steps=32256`,
    `actual_Adam_steps=8064`
  - update 64: `completed_updates=64`, `environment_steps=32768`,
    `actual_Adam_steps=8192`, `phase_complete=true`, parent SHA
    `443863dd...`
- 518 frozen-input entries were hashed; 0 missing, 0 mismatched.
- `update-64.pt` is a `complete_update_boundary=true` checkpoint and reports
  `phase=1, half=1, admitted_stage_rows=2048, suffix_stage_rows=2048,
  total_native_stage_rows=4096`.

This is evidence that the saved update-64 boundary and raw data are internally
consistent. It is **not** an official `audit.py` result, because the stage's
`RESULT.json` is `passed=false`; `audit.py` refuses failed stages. The stage
record is incomplete and the checkpoint has not been accepted by the registered
controller.

## Scientific status

- Qualification is engineering evidence only: mechanism worked, zero optimizer
  steps, no training claim.
- Both micro stages are valid one-update engineering stages, not a scientific
  comparison.
- `control-phase-1` has no accepted two-update stage result and no official
  audit. Its update-64 checkpoint is a validated *candidate boundary*, not a
  completed registered stage.
- No paired phase result, no 96-game DEV, and no final test were produced.
- No unit-count decrease is called a combat casualty; no population win rate,
  confidence interval, or promotion claim is made.

## Decision required

Default: **stop here**. Preserve the evidence, publish the engineering stop, and
do not spend more GPU time on this experiment until root reviews the resource
gate and the update-64 acceptance question.

If root explicitly authorizes recovery, the least invasive option is a new
written recovery protocol that:

1. performs a second independent read-only audit of the stopped stage and
   explicitly accepts or rejects update-64;
2. records that the official stage audit is absent and why;
3. runs `candidate-phase-1` from 62 to 64, then paired phases 2 and 3 to 68,
   without replaying or reseeding the control data;
4. logs the actual `MemAvailable` and swap values on every post-update check
   before asserting, so a future stop is attributable;
5. keeps the registered factor, budgets, DEV design, and final-test boundary
   unchanged.

A rerun of `control-phase-1` from 62, or a new seed, is a retry/reseed and is
not authorized by this report. Declaring a new experiment from parent 60 would
be a separate scientific experiment, not a recovery of this one.
