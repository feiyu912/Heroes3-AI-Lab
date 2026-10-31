# Supply-aware visible v1: native development pilot registration

This registration precedes any native v3 supply-aware game. The policy is a
fixed candidate override, not a learned economy policy, expert certification or
native enemy interception predictor. The baseline index remains the frozen
strategic model's own choice; the candidate changes only its legal target index.

## Fixed dispatch rule

Only kind4 may override, and its destination must match a town in current
own_towns. Require transferable army_value / own_army_value >=0.25; compare
relative gain divided by(0.5+actual native path_cost), threshold0.60. The fixed
8-tile visible stronger-enemy proximity metric adds bounded urgency and prefers
a less exposed NEXT step. No remaining enemy movement, hidden future or native
interception access. Malformed/missing fields, old schema, zero own army, no
matching town, insufficient gain or too much path cost preserve baseline.
Constants are specified in supply_policy.py and are not fitted to this pilot.

## Registered 16-game design

Two existing TRAIN fixtures:
Maps/adv/takeover-v2-train-01-mines and
Maps/adv/takeover-v2-train-02-development (the latter is a TRAIN split despite
its filename). Director both red and blue; opponent Nullkiller2. For each map
and side use seeds2026101851 and2026101852. Each map/role/seed is paired between
the frozen learned baseline and the SAME baseline with supply-aware-visible-v1.
Exactly16 games, eight pairs, two map clusters. Unseen test stays locked.

Freeze exact model SHA, v3 native/source SHA, broker/encoder SHA, policy SHA and
maps before game1. New run directories, shared simulation lock, no concurrent
GPU learners. Log the baseline choice and actual overridden choice separately.
If code changes, end the old protocol and preserve its outputs before a new run.

Primary endpoints, all reported independently:

- Native terminal winner paired delta, with no timed-out/invalid outcome counted.
- First original main-hero loss day (starting hero stable ID, not replacement),
  with terminal-alive or unknown cases explicit; no invented death for betrayal.
- Actual reinforcements delivered: before/after native transfer, creature
  conservation and own army change, not candidate selection or town arrival.

Secondary diagnostics: number of triggered returns, full arrivals/transfer,
garrison backlog, native calendar day, resource cost and runtime. A legal override
is engineering success only. No improvement claim from a single favorable cell.

Stop for any illegal action, missing native terminal, missing/ambiguous ACK,
changed frozen input, crash or timeout. Preserve raw traces/partial state. Do not
turn an invalid run into a loss/win or silently replace it with a convenient seed.

Progression gate:16 valid games, at least two distinct map/role cells with actual
delivered extra troops; no baseline win flipped to loss; positive aggregate
delivered reinforcement difference and no earlier original-hero loss attributable
to an observed return on either map. Report win/hero-loss differences separately;
even a passed mechanism gate does not certify independent capability improvement.
Any native development/test protocol must be newly frozen after this analysis.
BC eligibility remains0 and no expert labels are created by this rule.

## Fair use of archived states

Old schema-v2 requests have no new native v3 fields. They must remain v2 and
fallback; never relabel them as actual native-v3 samples. A separate CPU fixture
may reconstruct an own-town value from an archived, player-owned state only,
provided it is explicitly marked reconstructed and its original trace/request
SHA is retained. Such a fixture tests parser/decision mechanics, not an actual
v3 game, native enemy visibility, a win counterfactual or demonstrated benefit.
