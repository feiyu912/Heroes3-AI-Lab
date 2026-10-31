# Native quiescence correction v4

V3 fixture solved the shared-target interference: both heroes actually moved in
both turns. Both raw runs nevertheless failed because the external runner killed
the process after a new request was sent, leaving an unmatched ACK. Do not reuse
either run as a pass, ignore pending requests, or relax request/ACK bijection.

V4 retains the exact v3 fixture and seed2026102501. Both candidates get the same
native hold instrumentation at the existing no-pending advanceTurn guard. Once
both mobile hero positions differ from their actual own-turn2 initial positions,
emit scheduler_quiescent_boundary and issue no more actions. Runner waits for
that native event AND its original strict evidence readiness before terminating.
The auditor requires exactly one boundary, no pending move/query/request and no
action after it. The common hold does not choose any hero or destination and is
inactive until both turn2 position changes. No close/transfer behavior changes.

All original gates retained, including per-hero motion in each of turns1/2,
native positive-MP garrison handshake/state/conservation and request/ACK bijection.
One fresh run per arm; baseline must be rejected for selecting garrison3 and no
unrelated reason, filtered must pass everything. Same map, same seed, one scheduler
predicate difference. Both locks in GPU->pool order; byte-exact accepted source
and executable restoration required before native runs. No PPO or final test.

New capsules are built because instrumentation changed. All older capsules and
failed raw evidence remain immutable. Success certifies only this isolated native
scheduler mechanism; it is not learned multihero play or a strength improvement.
