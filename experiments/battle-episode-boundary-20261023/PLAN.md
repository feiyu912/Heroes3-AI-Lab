# Phase-end terminal-drain prefix-credit extension — review design, 2026-10-23

Status: PLAN and CPU reference only. No runnable native/GPU/training controller is supplied, and no new native/GPU/optimizer work has been performed. The directory name records the original scheduling proposal; the identified learning factor is now **phase-end terminal-drain prefix-credit extension**, not pure map-switch timing.

## Question and common parent

Actual TRAIN audit found MMAI episodes averaging27.6–28.4 steps versus BattleAI18.6; phase-close unfinished rows22.8–24.3% versus13.4–14.2%. Both still have valid bootstrap. The question is whether observing the continuing episode's real terminal before constructing the final admitted rollout's targets improves learning. This is not a diagnosis that bootstrap was invalid or that missing terminals caused the earlier result.

Both arms start the same full control60 checkpoint: SHA`443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20`, completed_update60, environment_steps30720, cumulative actual_Adam_steps7680. Restore full role models, ordered named Adam states/hyperparameters and Python/NumPy/Torch CPU/CUDA RNG; never weights-only. CPU exact restoration has actually passed in `cpu-01/AUDIT.json`; CUDA remains unexecuted here. Both arms begin a fresh symmetric native epoch and never restore in-flight games.

Unchanged: last-graph mask; headsLR1e-5/bodyLR1e-6; terminal±1 and .5 potential, gamma1, lambda.95, step_cost0; PPO2epochs/microbatch8/clip.2/entropy.005/critic.5/max_gradnorm.5/targetKL.02;16workers; actual native BattleAI and original public CPU ONNX MMAI. No expert/DEV labels.

## Exact observation/admission budget

Use the existing seed2026102016 registered60-TRAIN-map curriculum, phases0..3 only:16 unique TRAIN cases, each with both roles/opponents,64 admitted transitions per cell. Each phase has4 cases×2roles×2opponents=16 slots. Native seed epoch:2026106800+phase*1000+slot, identical between arms. New independent drain-sampling generator seed2026106980+phase*16+slot; it must not advance the learner's Python/NumPy/Torch CPU/CUDA RNG. A generator draws every suffix action, and all actual outcomes/requests remain recorded.

Per slot/phase, both arms perform exactly:

1.32 admitted transitions → normal original GAE → PPO update1.
2.32 admitted transitions under the resulting fixed behavior model; **do not update yet**.
3.64 extra real native suffix transitions under exactly that same behavior model, private sampling RNG, zero PPO actor/critic/entropy loss membership.
4.Construct targets according to arm; PPO update2 on exactly the512 final admitted rows. Only then close that phase and start the next fresh mapped/seeded phase.

The64-step suffix is fixed for both arms even if the continuing episode ends early. After a real terminal, normal engine auto-reset may generate more same-case suffix observations; they remain recorded, zero loss membership, and cannot propagate across the first terminal into the prefix. This deliberately spends a symmetric observation budget rather than making faster-finishing arms receive fewer actual native observations. These extra observations are neither fictitious waiting/no-op actions nor new admitted training rows. Both arms close after the fixed suffix; this is not a test that every final native environment ends at an episode boundary.

| Stage, each arm | Admitted / loss rows | Extra native suffix | Total native transitions | PPO updates | Planned additional Adam |
|---|---:|---:|---:|---:|---:|
| First-phase micro stage |1024|1024|2048|2 (global61..62)|256|
| Full bounded stage, including micro |4096|4096|8192|8 (global61..68)|1024|

Every case/role/opponent cell contributes exactly64 admitted rows and64 suffix observations. No episode is omitted because it is long or loses. No admission quota is filled with duplicated/padded rows. Suffix after an early terminal is retained and explicitly unadmitted. Mainline checkpoints separately store `admitted_environment_steps`, `suffix_native_steps`, `total_native_steps`, inherited optimizer calls and new calls. Never inflate ordinary environment_steps with unadmitted rows or call them training examples. Full-stage expected cumulativeAdam8704; admitted environment_steps34816; extra suffix4096; native transition stage total8192. Counter conventions must be explicit in the schema.

## The only target difference

Let P be the final32 admitted steps/worker, S the64 recorded suffix steps. Preserve P's original reward/value/next_value/terminated/truncated arrays before any target work.

- Control computes original32-step GAE(P), including P's own last-observation value bootstrap. The suffix cannot alter any control targets, RNG or loss row membership.
- Candidate checks whether P ends in an ongoing episode and its first actual suffix episode end is a **normal terminal within64 steps**. If so, compute unchanged gamma1/lambda.95 GAE on concatenated P+S and retain only P's32 advantages/returns. A first terminal cuts propagation; subsequent auto-reset rewards have zero influence. Earlier episodes already terminated inside P also remain unchanged.
- If P already ended, if the suffix cap contains no terminal, or if its first end is a nonterminal truncation, candidate keeps the exact original GAE(P). Report a cap/truncation and preserve the original bootstrap; never assign a loss or invent a terminal. All suffix raw observations are retained in either case.

No suffix action/value appears as an actor/critic/entropy loss row. Its actual reward/value residuals can influence eligible prefix targets only in candidate; this is the named single learning factor. PPO advantage normalization still operates on the same512 admitted rows and is an intended consequence of target changes. All P+S actions used for extension come from one unchanged behavior policy after update1 and before update2; neither arm may update during suffix sampling. The first32-step update of a phase is already complete and is never retroactively relabeled or updated again.

`credit_extension.py` is a CPU math/reference interface, not a native qualification. Production integration must preserve original float32 baseline GAE; `target`'s float64 calculation is a CPU numerical reference. Save the actual old P next_value, first-terminal position, extension eligibility/reason, baseline and candidate targets, and suffix rows' explicit zero loss weights. Independent reviewer must recompute targets from raw P+S.

## Qualification before finite training

1.CPU completed: actual exact control60 model/Adam/RNG restoration; both terminal reward signs; no post-reset leakage; earlier prefix episode isolation; exact-boundary case; cap and nonterminal truncation fallback; last-row bootstrap; original float32 GAE agreement; private RNG preservation; identical per-cell/native/admitted budget ledger. No native/actual gradient qualification claimed.
2.Future native qualification, after root review: one phase,16 staged workers,2048 actual transitions, **zero optimizer steps**. Sample one restored fixed behavior policy and derive both targets from the same saved P+S. These are mechanism observations, not successful training or expert data. Require actual extension in at least one continuing prefix, real normal terminal, unchanged model/Adam, exact sampling RNG separation, complete native-step evidence and ordinary process shutdown. If this fixed fixture has no eligible extension, qualification is inconclusive; preserve it, do not reseed until a passing example. Root reviews any added fixture as a new registration. Mechanism sampling does not advance either future training chain's parent RNG.
3.Future paired microtraining: execute each arm's phase0 serially with separate new native environments from the same parent/RNG. Save complete61/62 boundaries and actual hook counters. No DEV. Require exact admitted/native quota, target reconstruction, unchanged frozen parameters, no invalid native returns and explicit cap rates. A learned update's actual Adam calls must be recorded, never inferred from planned minibatches.
4.If microtraining engineering checks pass, extend those same optimizer chains through phases1..3 to global68; do not discard/replay phase0 or reset Adam/RNG. All sources/contracts/native dependencies freeze before phase0 and remain unchanged through both arms. A native phase boundary at62 is naturally fresh for phase1; a user interruption midphase requires a separate recovery review.

## Limits, failures and fair optimizer accounting

Extra64-step observation budgets are exactly symmetric; trajectories, realized episodes, first-terminal distances, wall time and NPC action counts may diverge after targets change. Report them; they are not equalized by claiming equal compute time. Conditional terminal-within-cap eligibility can depend on policy and should be reported by role/opponent/family. It is a bounded target-extension algorithm, not an unbiased estimate of all eventual returns. Cap fallback includes both wins and losses without outcome selection.

The unchanged PPO implementation may early-stop at targetKL.02. Therefore exact planned128 actual Adam calls/update cannot be guaranteed before real execution. Do not disable KL stopping or add extra updates/rows to force a matched budget: that would change another factor. Before advancing paired phases, compare actual counters. If either arm deviates from planned counts or arms differ, retain the learned outputs and raw evidence, stop the registered matched-budget experiment, and report **optimizer-budget mismatch**, not a game defeat or fabricated exact fairness. An unmatched result is descriptive only and cannot certify this exact-budget comparison. No retries/reseeding to obtain a passing arm.

Native request hard timeout90s; suffix phase wall cap300s; normal64 suffix-step cap. A time/resource error is an engineering stop with raw pending evidence, not a scored loss. The64-step no-terminal cap is a normal algorithm case with original-bootstrap fallback and does not trigger reseeding. Prephase availableRAM>4GiB/swap<256MiB/disk>10GiB; original16-worker staged boot and postupdate>2GiB reserve. Acquire GPU→pool, single learner, serialize arms. Collect suffix CPU payloads without retaining inference graphs; verify available memory before the first actual training stage. This plan starts no process or lease.

## Final bounded evaluation, only after final68

Register one96-unique-game DEV set: shared control60 parent32 + control-prefix-only final6832 + candidate-extension final6832; cases192..199, both roles, actual BattleAI/original public CPU ONNX MMAI, seedbase2026107600+case_index*100. No interim DEV or checkpoint selection. Use the repaired pending→parent-finalization recorder and full per-step graph/probability/action/native returns. Independently replay all scored games and calculate paired flips/loss efficiency. The existing final test set is not used. Small DEV results remain developmental evidence; no automatic promotion or95% claim.

Proceeding beyond this PLAN+CPU package requires root's implementation review and a new frozen executable package; there is no authorization inferred from these hypothetical future-stage results.
