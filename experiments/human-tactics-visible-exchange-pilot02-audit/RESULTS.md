# Real paired pilot: gate failed

Execution repair: the earlier pilot failed before native environment creation
because the copied provenance helper referenced missing PLAN.md. Its original
log/protocol remain unchanged. The repaired directory freezes the actual
PREREGISTRATION.md and exercises freeze/verify for both train maps before play.
Algorithm SHA remained f1e946efece748a68d2c0b758b380aa6b2baa5604e1996fbd77d78ce26e315c3.

The repaired pilot completed the exact preregistered 16 native games (2 used
TRAIN fixtures × 2 roles × 2 new seeds × 2 methods) under the shared simulation
lock, serially, without a GPU learner. All 357 actions were legal with freshly
recomputed matched native START/FINISH windows. All terminal BATTLE_END/winner,
casualties, archives and frozen inputs passed the independent read-only audit.
The audit also recomputed every candidate action from its archived public graph;
all matched actual execution. The two members of every pair had identical
initial public graphs. Locked development/test were not played.

Teacher2 won 4/8; visible-exchange-v1 won 4/8. All eight paired win deltas were
zero. Mean main permanent casualty delta and total casualty delta were both 0.
There were four actual overrides, confined to fixture1 in both roles. Thus this
was not a complete no-op, but it failed the preregistered strict casualty
improvement gate. These 16 games are development data, not an independent
capability test or a meaningful standalone win-rate estimate. BC eligibility 0;
no expert certification, model training or promotion.

## What the failures show

On fixture1 attacker, step13 changed a teacher estimate near -6 permille to a
zero estimated net exchange. Actual strict-window events show the selected
single pikeman hit another pikeman for 1 or 2 damage, got a 2-damage COUNTER,
and killed nothing. One seed's final main loss rose by 2, the other stayed
unchanged. A locally less-negative pairwise estimate therefore did not secure
permanent material benefit or later positional/tempo advantage.

On fixture1 defender, step11 changed an estimate of 0 to about +5 permille.
Actual events show 8 damage killing an enemy single pikeman, without a COUNTER
inside the action window. One seed's main loss fell by 2, the other stayed
unchanged. The improvement and deterioration cancel in the full registered set;
selecting only the favorable defender cell would be post-hoc selection.

These events support a narrower next hypothesis: a score change from negative
to zero is not enough reason to override the stronger exchange-order teacher.
A future candidate could require strictly positive estimated permanent gain,
but cannot claim the retrospectively selected subset as new evidence. Register
that candidate separately with fresh seeds and retain all results. More broadly,
one-step pairwise scoring does not resolve target removal, occupancy, next-own
action and opponent-response interactions; increasing game count with the same
score is not an evidenced fix.

The native evidence does not uniquely attribute the two-unit terminal delta to
one mechanism; later policy actions and RNG consumption also diverge after an
override. No future-seed branch oracle or invented expert label was used.

## Reproduction and immutable outputs

Raw games and frozen source snapshots:
`experiments/human-tactics-visible-exchange-v1-pilot02/runs/train/`.
Execution aggregate: the sibling PILOT_RESULTS.json.
Independent recomputation: this directory's audit.py, audit.sh and AUDIT.json.
audit.py refuses to overwrite AUDIT.json. Reproduction uses a fresh output
version; never rerun into the existing game directory.

The earlier 75-game audit remains separate. This pilot adds 16 games and 357
actions; combined v3-family engineering/diagnostic count is 91 games and 2,154
actions, not an independent evaluation sample or a training gain claim.
