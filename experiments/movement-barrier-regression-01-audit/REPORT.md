# Movement barrier: functional regression passed, exact295-prefix condition not met

One authorized native game reproduced the old engineering failure's train01,
blue Director, EmptyAI, seed2026101860 and fixed legacy checkpoint. No additional
game or test was run. The original comparison runner's STATUS.json remains
failed: request/action273 differs from the old run, so it cannot be described as
an exact295-action counterfactual. Separate read-only evidence explains that
divergence and verifies functional correctness without rewriting that result.

## First difference explained by correct post-battle observation ordering

Requests/actions1–272 are byte-identical. Old decision273 still commits to a
defeated neutral target at(7,34,0); new decision273 no longer contains that target
and selects another currently legal destination. Checkpoint, broker/model/encoder
code, map bytes and run-local Castle config match exactly. The native source
diff is the declared movementBusy barrier, trace markers and removal of the
battleEnded immediate continuation.

The native logs identify the preceding neutral guard as object160, griffins.
Old log30479 receives BattleEnded; old30509 sends decision273's next MoveHero
before client guard removal30518. In the new run, client guard removal30498 is
fully applied30503; the original visit and movement queries have popped and the
client receives PlayerBlocked解除30512–30516; only then new30522 sends the next
move. FIRST_DIFFERENCE_CAUSE.json preserves both contexts and exact source hashes.
The stale guard therefore disappeared from the new candidate list because the
barrier waited for native post-battle state application, not because of modified
policy inputs, map/seed/weights or artificial state. A single new trajectory
still cannot isolate a causal win effect.

## Full native/ACK acceptance

The new game has307 issued moves and307 successful matching move_applied ACK
states, including the last request. A pending-move scan verifies no overlapping
request and no unconfirmed final action. There are no move_failed/economy_failed
states; no before-action state after terminal; both QueryReply submissions have
successful native application, with no server must-answer-query rejection.

The independent generic raw audit also passes: native normal terminal/winner,
legal selected candidate, file/request/action/native consumption hashes and
troop-transfer conservation. Director wins and the original main hero survives;
148 troops are delivered to it. This is an engineering game versus EmptyAI,
not a model improvement result, learning update or expert certification.

The formerly numbered295 action is no longer the same state/action because
observations legitimately diverge earlier. Do not claim it was replayed exactly.
Its underlying failure class (moving before the original visit/movement query
fully drains) is directly tested here with zero rejected moves globally.

## Preserved evidence and next execution boundary

run-01/STATUS.json and initial comparison failure remain unchanged.
run-01/RAW_AUDIT_READONLY.json contains the successful independent episode audit;
PREFIX_DIAGNOSIS.json records all23 request and2 action differences through295,
307 confirmed ACKs, final action and terminal, plus the full native source diff.
FIRST_DIFFERENCE_CAUSE.json binds native ordering around the first difference.
The successful functional interpretation is separate from the failed exact-prefix
condition. No strict legality/ACK gate was relaxed.

The parent has reserved the shared pool for the two-environment collector.
Acceptance-02's four engineering games and eight gated NK games have not begun;
they will start after the parent releases that reservation, using a fresh
freeze and output directory. BC eligibility remains0.
