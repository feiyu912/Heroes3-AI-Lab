# Four training losses: supply worked, force scheduling and threat input did not

Scope: only the four Nullkiller2 losses in takeover-03/native-boundary-01/
continuous-2/training.json. Both TRAIN maps and both Director roles are covered.
The second map's filename contains `development`, but its split is TRAIN; no
unseen test was read. No simulation, GPU work, training or frozen-input edit.
AUDIT.json verifies the training-registered SHA of every client log, state trace,
decision trace and target trace; DETAILS.json additionally binds all 706 consumed
public requests by SHA and matches each against the native decision line.

All line numbers below are one-based in the respective native run directory
recorded in AUDIT.json. A decision count is not a count of battles.

| Seed / map / Director side | First-day supply | Later decisive chain | Native finish |
|---|---|---|---|
| 2026101912 / mines / red | Recruited 9 creature2 +14 creature0; transferred both, hero became 34/19 at trace13/15 | Strong visible hero 9166 vs own5114 on day3; own town absent at trace93/day5, recaptured by trace118/day6 with army reduced to 13 creature0; lost again trace131/day7; no town thereafter | trace269/day13 defeat while hero still present in trace; log36263 gives hero betrayal message, so do not call this an ordinary main-hero combat elimination |
| 2026101913 / mines / blue | Same successful 34/19 by trace15 | Original hero1 removed between day6 end/trace128 and day7 start/trace129; native log23654 confirms removal. Day9 garrison26 troops at trace183, day15 garrison72 at trace307, but hero26 stays21/7. Hero26 disappears trace345/day17; replacement14 finally receives full supply at349/351 then disappears with town at371/day18 | Native defeat log51764; four own heroes removed over the episode |
| 2026101922 / development TRAIN / red | Same successful 34/19 by trace15 | Day8 garrison21+13 at159/161; day15 garrison42+26 at305/307. Main hero2 remains25/17 and disappears409/day20. Its last own turn had visible threat30825 vs own4142 (target224/day19), while 68 troops remained in town. New hero30 loads all68 at413/415; own town absent433/day21; hero30 later removed | trace531/day25; native log52991 removes main2, log72143 removes replacement30, native defeat72220 |
| 2026101923 / development TRAIN / blue | Recruit succeeded but hero3 never collected it: trace7 town14+9; trace26/day1 end hero still20/10 | 28 valid reinforcement opportunities, zero selected. By trace157/day8 town35+22 but main remains20/10. Last own turn day9 sees threat14989 vs own2860 (target91); main disappears193/day10 (native log41727). Replacement25 receives supply197/199, temporarily captures town11 at260/day12, then disappears263/day13. Repeated rehiring includes one-unit armies, nine hires total | trace567/day27: no heroes or towns; native defeat108501, remaining gold15540 |

The second/third/fourth runs demonstrate native hero removals rather than a
mere logging omission. For each removal the log contains server and client
copies; DETAILS.json does not count the two lines as two separate hero deaths.
The raw logs include native BattleResult/finalization around removals. They are
not a full tactical event archive and do not establish the exact causal attack,
initiative mistake or win counterfactual for every loss.

## What is and is not broken

Recruit/build/transfer ACK machinery runs: all four recruit, three collect the
initial troops on day1, later hired visiting heroes collect garrisons. This
rules out the blanket diagnosis "recruitment does nothing". The fourth run and
the weekly backlogs show a force-delivery policy failure instead. Reinforcement
candidate-present/selected decision counts are respectively 2/2, 15/3, 23/2,
28/0. A remaining weakness is the fixed reinforcement benefit5, independent of
garrison size, and no garrison-value input for the learner.

Exploration selected58/102/141/147 times respectively, while strong enemy targets
are strength-filtered. Retreat/defend/hold-town are not explicit candidate kinds.
Attacking weak visible targets and avoiding a strong attack target is therefore
not equivalent to keeping a main hero out of a stronger enemy's next turn.

The highest-confidence functional information defect is visible-threat erasure:
the frozen CDirectorAI.cpp logs and drops an enemy hero once its visible coarse
army estimate exceeds0.9×own (lines164–175). The serialized public request
(lines664–685) contains own army value, resource/position/movement and candidate
kind/geometry/path/score only. Neither rejected visible enemies nor threat ratios
are supplied. The 11-state/15-candidate feedforward encoder also has no enemy
list, garrison magnitude, town survival countdown or threat memory. Updating its
weights cannot distinguish two otherwise equal requests whose only difference
is a nearby filtered strong enemy. This is a representation/action-interface
limit, not evidence that PPO has learned and rejected safe play.

There is also a learning weakness: the valid reinforcement choices exist and are
often ignored, including all28 opportunities in the train02 blue run. Four sparse
terminal losses do not identify reinforcement timing, and no separate training
gain is established. The amount of existing training is not itself evidence
that more identical updates will fix the missing information.

## One next mechanism with the strongest support

Implement a **visible-threat survival gate for strategic destination choices**
in a new protocol/version. Build a threat list from the same lawful visible
enemy observations BEFORE filtering offensive candidates; keep the coarse
strength/known location/observation day even when attacking that enemy is rejected.
For each candidate expose nearest stronger-enemy distance/strength ratio and
whether its proposed end-of-turn area increases exposure. Provide at least one
legal own-town/safe-retreat/hold-turn fallback so the gate can avoid exhausting
movement near an obviously superior visible army. If all choices are exposed,
report uncertainty and choose the least exposed legal fallback rather than
inventing safety or reading hidden enemy movement/RNG.

Start conservatively with the two observed last-turn failures: day19 seed1922
(30825 vs4142) and day9 seed1923 (14989 vs2860). Derive routing from public terrain
and observed enemy army/speed bounds; exact enemy remaining movement is not a
permitted hidden shortcut. This gate is a heuristic until native tests verify it;
distance is not a proof of attack reachability. It should make safe return for
already recruited reinforcements possible, but no claim is made that it saves
these games or replaces the separate garrison-valuation improvement.

Before more PPO, freeze the new interface, verify that two requests with identical
current geometry but different public threats produce different risk features,
then run paired fresh TRAIN seeds versus the prior model: log first main-hero
loss day, actual delivered reinforcement value, held-town days, and native final
outcome separately. Verify the gate never selects an action outside the real
legal set. Only after that mechanism check perform a new paired dev protocol;
unseen test stays locked. This is a specific structural repair to test, not a
promise that a fixed distance threshold or extra training rounds will win.

## Reproducibility

audit.py writes AUDIT.json from immutable input records; details.py writes
DETAILS.json; threat_links.py writes THREAT_LOSS_LINKS.json. Each refuses to
overwrite its evidence output. Run with the CPU Python under WSL in a new audit
output version. Every native path and input hash is retained in the JSONs.
The four frozen CDirectorAI.cpp snapshots have the same SHA:
766feddef8cd976222fa8e471915c7e74367f99702f6fdb4a64a729717b3ef54.

This audit establishes a reproducible failure chain and interface limitations.
It does not isolate causal win effects, certify a new policy or consume a test set.
