# Positive exchange v2: frozen development mechanism probe

Status: CPU replay only; zero new native games, zero optimizer steps.
Not a human expert, learned policy, or certified curriculum.

Hypothesis: refusing zero/negative estimated exchanges prevents low-value attacks
that merely consume a retaliation without obtaining immediate material advantage,
while retaining positive alternatives. Candidate differs from visible-exchange-v1
only by requiring selected net_permille > 0, plus the existing >1 permille gain
over teacher. Native teacher2 controls WAIT, MOVE, DEFEND, special attacks and
unknown estimates. Pairwise expected graph value is NOT permanent unit gain.
No event history, actual seed, outcome, quality label, hidden counter budget,
future RNG, or offline rollout result enters the deployed decision.

Exactly 16 NEW games: reused TRAIN fixtures 0 and 1, attacker/defender, seeds
2026111801 and 2026111802, native teacher2 versus positive-exchange-v2, BattleAI
opponent. Eight paired units are two map clusters, not eight independent maps.
This is a new seed development diagnostic, NOT an independent skill test.
No locked development/test map is consumed. Baseline first within each pair.

Primary terminal outcomes, kept separate: native win delta; permanent casualties
of creature 6; total permanent casualties. Negative casualty delta is favorable.
Do not sum different creature counts into an arbitrary training reward.
Environment step reward is archived for provenance only and is not used for
selection/training/promotion. For any later learning protocol, terminal win/loss
would be +1/-1 with gamma=1; that protocol is NOT authorized by this experiment.

Mechanism diagnostics: count overrides in each fixture/role, actual strict-window
damage/kills/counters, zero-or-negative estimated override count (must be zero),
and full terminal consequences. Mechanism counts are NOT reward. Report every
cell, including worsened ones. No post-hoc favorable-role exclusion.

Reject/stop on illegal action, truncation, nonzero exit, missing BATTLE_END,
incomplete action window, changed frozen SHA, or missing native normal terminal.
Invalid games are neither losses nor wins; preserve all partial files. SHA bind
candidate, all copied dependencies, maps, runtime libraries/connector and heroes
before game1 and verify each step. Do not edit inputs after freeze.

Progression requires 16 valid games, overrides in >=2 fixture/role cells,
zero baseline-win to candidate-loss conversions, aggregate main casualties
strictly lower, total casualties not increased, and neither map's aggregate
main casualties increased. A no-op or failed gate rejects advancement.
Even passing permits only a separately registered broader development study;
BC eligibility remains zero pending new independent certification.

launch.py defaults to read-only plan. Only the root agent may schedule
`launch.py --execute` after native resources are free. Episode runner obtains
the standard shared simulation lock serially; no GPU or compiler is used.
Never overwrite runs or reports. Historical input files remain read-only.
