# Real garrison scheduler qualification v2

Engineering mechanism test only. No PPO, policy broker, final test, strength score or model promotion.
Original probe-v1 remains failed and immutable. Map bytes remain identical; a real native
GarrisonHeroSwap changes its visitor into an owned garrison before any scheduling.
Both arms use identical setup/instrumentation/map/seed 2026102501 and thread server.
Only filtered adds rejection of hero->isGarrisoned() to pickHero eligibility.

Run baseline once and filtered once, no reseed/retry. Each uses fresh attested capsule
and output directory. GPU learner lock then pool lock, both nonblocking, protect native
execution and compilation; accepted source and binaries must be restored byte-exact.

Common strict gate:
* One setup requested/sent/successful ACK with unique positive request ID, before any selection.
* Raw prestate is owned visiting hero3, no garrison; raw poststate is real garrison3,
  no visiting hero, matching town ownership/reference and strictly positive movement.
* Setup conserves seven resources, hero identities/owners/positions/movement,
  creature totals (deduplicate town upper-army aliases), town buildings and stocks.
* In each of own turns 1 and 2, each owned mobile hero0/2 has successful unique
  move_sent/ACK and actual position change. A successful end-turn ACK separates turns.
* Garrison3 remains in place and garrisoned; no scheduling or move request for it.
* No failed or unmatched move ACK, frozen-input drift, broker, timeout or native rejection.
* Actual executable/library identity and thread-server evidence must independently pass.

Baseline is a negative control: expect its scheduler to select positive-MP garrison3
and thus fail the same gate. It may make no move request if pathfinding blocks it;
selection itself is a gate violation. Pair qualifies only if baseline fails solely
for this expected exclusion violation and filtered passes all requirements. Otherwise
stop and diagnose; never relabel a failed arm or loosen the gate.

Stop after both mobile heroes show actual motion in both turns, not at game completion.
Timeouts/invalid fixture are engineering failures, never losses. All raw files and
failure capsules retained. Independent MiniMax review is advisory and separately
identified; actual qualification requires native raw evidence recomputation.
