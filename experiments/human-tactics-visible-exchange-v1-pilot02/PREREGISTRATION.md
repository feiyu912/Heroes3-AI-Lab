# Visible exchange probe, version 1

Status: executable candidate and read-only replay validated; no new games run.
This is a development hypothesis, not an expert, a trained model or certified curriculum.

## Hypothesis fixed before any new game

The v3 bait target override can choose a poor immediate exchange because target
value ignores retaliation cost. Compare the public graph's estimated net value
of ordinary legal melee alternatives instead. Keep the native teacher when the
baseline is not ordinary melee, an estimate is unknown, or gain is <=1 permille.
No WAIT override, secondary attack proxy, fixed highest-value bait target,
remaining-retaliations field, actual seed or future random numbers is used.
This is a one-action expected exchange probe, not beam search or minimax.

## Small paired development experiment

Run exactly 16 new games: old TRAIN fixtures 0 and 1, both attacker/defender,
seeds 2026101841 and 2026101842, methods native teacher2 and visible-exchange-v1.
The eight pairs share map/role/seed; they are only two map clusters, not eight
independent maps. Opponent is BattleAI. Use the supplied runner and shared pool
lock serially; launch no learner. Freeze policy, dependency, map and binary SHA
before game 1 and verify at every decision. Do not modify inputs mid-run.

Primary end points, reported separately: native terminal paired win delta,
main-stack (creature 6) permanent casualty delta, total permanent casualty delta.
All armies in these two fixtures use the same main/chaff types, so these counts
can be compared within each pair. Never use transient HP score as terminal gain.
Also report override count, legality, strict event windows, terminal completeness
and wall time; timeouts/crashes are invalid, not losses or wins. Any invalid
game stops the round; preserve its partial trace before analysis and correction.

Gate to a NEW, separately registered development protocol: all 16 valid, at least
two distinct fixture/role cells with overrides, no paired baseline win converted
to loss, aggregate main casualties reduced and neither map cluster worsened.
If no overrides, report a no-op rather than stronger teacher. If the gate fails,
do not train BC/PPO; inspect failure actions, then version a new hypothesis.
Passing this pilot is not independent improvement certification. Existing locked
development/test fixtures remain untouched by this executable (explicit guard).
BC eligibility remains zero until a separately frozen independent evaluation.

Example one game (requires root resource scheduling):

```bash
bash /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-visible-exchange-v1/run-events-lab.sh /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-visible-exchange-v1/run_episode.py --scenario 0 --role attacker --seed 2026101841 --policy visible-exchange --output /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-visible-exchange-v1/runs/train/0-attacker-2026101841-visible-exchange.json
```

The runner and unchanged dependencies were isolated copies of curriculum-v3;
run_episode changes only the policy hook and train-only guard. Native binaries
and all original archives are read-only. No GPU learner is instantiated.
