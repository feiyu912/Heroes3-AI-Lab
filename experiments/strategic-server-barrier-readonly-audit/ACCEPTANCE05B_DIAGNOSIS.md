# Original acceptance05b stopped, not recertified

The frozen original runner completed all four EmptyAI engineering games and one Nullkiller2 game with its strict raw checks. The next game (train01 red, seed2026101862) completed naturally but failed the original `audit_supply_raw.py:35` condition that the last trace record must be victory/defeat. The original batch remains failed and stopped; later six NK games were not started.

Four engineering results: wins at days19/33/29/15; building33 preceded32 in all four; >=5 actual recruited and transferred creature types; conserved transfers169/148/268/74 to the original hero; all final actions confirmed and no query failures. These demonstrate scripted mechanism execution, not learned improvement.

First valid NK result: loss day41, original hero removed day40,206 real transferred troops; fully passed original strict audit. The second NK native result reports loss day46,314 requests/314 confirmed,0 failed moves. It is excluded from original valid batch results pending an explicitly versioned audit.

Raw second NK evidence: `/root/heroes3-ai-lab/workers/adv-runs/economy-v4-nk-development-map0-red-2026101862-2026101862-0ckyyrdt`. client.log SHA256 `4f42199d61ec700b9db84420f1cfb8cef7b1c1b1f2aa75ce678241dafc35e403`; strategy-trace SHA256 `0dc2ae6b3e6a5582eecce17caace4666d5c6c357a6f17a7f2d8294b052b5a9e2`; decisions SHA256 `bf03b9f8668f0b2ecc0856eba38b8c2af6cf661fa80e373d20070c7b045924a8`.

Last trace sequence is before_recruit → economy_applied → turn_end → native_battle_blocked → defeat → native_battle_ready. END writes an observation after terminal; it issues no action because turnActive is false. Native log120311 consumes red's defeat; server had emitted barrier-ready120248 after its request ACK120247, then client processes END. Later QueryReply requests in the log belong to Nullkiller2's winning hero's remaining levelups, not Director. There are no `Got false`, `not allowed`, query rejection, failed-action lines in the whole log.

This is a trace-tail compatibility issue, distinct from acceptance04's actual spurious movement. Any new audit version should require exactly one terminal, permit only explicitly named passive `native_battle_ready` records after it, and continue to reject all `before_*`, new Director requests, unpaired movement/economy ACKs, native rejection and unchanged-input failures. It must re-read the full original raw files rather than edit/filter evidence files. This report itself does not change the gate or certify the failed episode.

The game and runner exited naturally; read-only process inspection found no remaining VCMI game process. No further games have been started.
