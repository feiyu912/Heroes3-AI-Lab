# Scheduler garrison fixture v3

V2 failed both arms: native setup was valid and filtering excluded garrison3,
but heroes converged on the garrison's reinforcement army and opened an unhandled
exchange in turn2. Both timeouts remain failures. No retry or gate relaxation.

This new experiment changes only fixture geometry relative to v2. Reuse the
exact v2 baseline/filtered compiled capsules and instrumentation, including its
schema label. No source rebuild or exchange/transfer changes. New geometry is
explicitly materialized and fully listed in FIXTURE_DERIVATION.json: water y9
separates town from both mobile heroes, water x9 separates mobile compartments,
water x26 separates the enemy; four existing resource objects move to two goals
per mobile compartment. Hero/town data and header are unchanged.

Both arms use this identical new map and seed2026102501, once each, fresh output.
All v2 strict criteria remain: real positive-MP native garrison before scheduling,
setup conservation, each mobile hero actual movement and paired ACKs in BOTH
turns1/2, successful intervening endturn, no control selection/movement, no timeout,
rejection, frozen drift, broker or unverified library/thread mode. GPU->pool
nonblocking lock order remains. No PPO, final test, game score or strength claim.

Baseline must fail the same gate through selecting positive-MP garrison3;
filtered must pass every requirement. Pair qualifies only if the baseline has
no unrelated failure. If garrison move attempts are rejected natively, retain
the raw failure, attribute it explicitly to that excluded control and do not
call baseline a pass. Extra mobile/fixture/timeouts invalidate the pair.

All failed v2 raw files and original v1/v2 close/transfer evidence stay immutable.
This qualifies an isolated scheduler mechanism only, without certifying a learned
multihéro policy, full-game strength, recruitment learning or courier strategy.
