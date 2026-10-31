# Independent bounded-replan audit v2

The completed 8-pair / 16-game diagnostic batch passes the new CPU-only independent audit. Original runner, original auditor, native candidate, game outputs and original results were not changed. No new game, GPU operation, optimizer step or training admission occurred.

Entry points are `audit_replan_v2.py` (one terminal game), `review_completed_pairs_v2.py` (the completed batch) and `check_audit_replan_v2.py` (artificial CPU predicate fixtures only).

## Real evidence

`review-v2-native-01/AUDIT.json` passes all 16 arms, covering 3,542 actual policy proposals and 2,482 observations in which the previous same-hero/same-own-turn committed goal remains admissible. There are 17 authenticated releases, all with multiple immediate next tiles, no repeated hero/turn budget, and no changed selected goal or next tile. This reproduces the original mechanism counts. It does not establish safe retreat or a causal victory improvement.

The revised checks bind the core proof's owner and **all five** `raw_sha256` files to the current game directory; verify the exact source SHA of both recorded core auditors; validate original request bytes, response/action files and proposal SHA for every policy decision; and independently re-extract the actual native server-apply / exact ACK event stream and rerun the full execution contract. The new output records the exact SHA of every request, action, broker proposal file and consulted audit source.

Every proposal is then checked, including proposals with **no** release event. If the latest selected move's `(destination, kind)` is still in the current legal pool, the pool must contain one move unless that exact request carries the single permitted release. This closes the old verifier's omission of unlogged reopening in off mode or after the budget has been consumed. Natural disappearance of a goal remains allowed to expose alternatives. A different own-turn identity starts an independent budget. EndTurn remains a player-wide native action and never becomes a move goal.

The terminal `RESULT.json` was checked before reviewing the batch. Its SHA is recorded as `dd3ae40282e2c62e832f516fa859a4e26880469c912351f5ce426ca9ad5600e8` and checked again after all reviews. Each real-arm report records current raw/proposal/request/action/source hashes. Original Linux evidence remains in `/root/heroes3-ai-lab/evaluations/typed-bounded-replan-paired-01`.

## CPU rejection coverage

`review-v2-cpu-01/AUDIT.json` passes five positive narrow predicates and 18 rejection cases: swapped proof, wrong owner, incomplete hash coverage, changed auditor source, changed raw file, deleted release in both mirror and sidecar, unlogged multi-move pool in off mode, logged release in off mode, logged or unlogged second use of budget, wrong old goal, unpublished/weak threat, duplicate release, out-of-order decisions, proposal SHA mismatch, changed action file and semantically unchanged request with different bytes.

These fixtures are explicitly artificial, `fixture=true`, `real_execution_certified=false`, with zero native games. They call narrow proof-binding / candidate-transition / IO-binding predicates and cannot produce a whole-game certification. Actual original game files were never used as mutable fixtures.

## Remaining scope limits

This audit covers raw execution bindings and the bounded availability/commit contract. It does not repair the frozen paired runner's causal-prefix diagnostics. In particular, zipped prefix comparisons can omit a length-only difference, and comparing both arms' latest decision counters can misclassify a pre-intervention NPC difference. A separate independent causal audit must examine full sequence lengths and the candidate arm's real release position. Same seed/binary and an initial matching request do not prove the complete hidden opponent chronology is identical.

The mechanism has not changed an actual selected goal in these 17 opportunities. Therefore neither a retreat skill nor an ability gain can be attributed to this diagnostic batch, and no default promotion follows from the engineering checks.
