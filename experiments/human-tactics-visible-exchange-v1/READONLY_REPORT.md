# Takeover evidence review and executable candidate

Fresh read-only verification covered all 75 v3 summaries and gzip archives:
their registered summary SHA, archive SHA, 1,797 legal selected actions, strict
matched action windows, final native BATTLE_END/winner, and zero BC eligibility
all passed. No historical source or binary was modified. The audit checks the
raw records directly rather than treating prior report text as authority.

Freshly recomputed paired results agree with prior reports: v1 and v2 each have
eight pairs, mean main casualty delta -0.125 but net wins -1; v3 has eight pairs,
mean main casualty delta +0.5 and net wins -2. These are reused training fixtures.
The direct terminal evidence therefore rejects certification of every version.
The earlier mechanism count is not a reward: spending a counterattack is useful
only if the later attack's savings exceed the bait sacrifice and lost initiative.
v3's zero WAIT overrides and remaining losses isolate target selection as another
failure mode, but do not prove it is the sole cause.

The new visible_exchange.py replaces target-value priority with the current
public graph's expected net exchange estimate, and only compares ordinary melee
actions of the same active unit. Native teacher2 is the fallback; WAIT/DEFEND/
movement and secondary attacks remain with the baseline. This explicitly tests
whether accounting for an immediate sacrifice/retaliation cost helps. It does
not represent joint action order, occupancy changes or independent future RNG;
it is a narrow falsifiable candidate, not a stronger-search claim.

Offline replay of eight v3 TRAIN teacher trajectories covered 186 decisions,
produced 4 different legal actions, and preserved behavior after adding arbitrary
seed, event, outcome and withdrawn quality fields to the input. Those fields are
explicitly projected out. Unknown/NaN/infinite baseline estimates preserve the
teacher. This is an engineering input/legality check; outcomes after these new
actions have NOT been simulated. Current new game count is zero.

READONLY_AUDIT.json binds all raw input hashes and the policy SHA. Reproduce it
only in a new output version (the script refuses to overwrite the existing audit).
PREREGISTRATION.md fixes 16 games, seeds, train-only fixtures, paired endpoints,
failure handling and progression gates before new execution. run_pilot.py is a
serial runnable entry point when the root agent schedules the shared pool.
No GPU learner, clone interface, future-seed oracle, withdrawn expert label or
locked development/test game was used. BC eligibility remains zero.
