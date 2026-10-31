# Server barrier and economy acceptance06

Original registered acceptance06 completed all12 games in154.89seconds: four EmptyAI engineering wins and Nullkiller2 development1/8. Both use the same old parent checkpoint, argmax legacy projection, scripted economy and zero optimizer updates. These scores are development observations and do not establish economic causal benefit, learning improvement or independent generalization.

All12 RAW_AUDIT.json files passed. Independent full-log reread (`ACCEPTANCE06_RAW_REVIEW.json`) verified **5076 paired Director movement requests/ACKs,134 successful QueryReply requests across both players,0 server rejection lines,0 unconfirmed final movement and0 postterminal Director actions**. All movement START/END counts match. Native source, binary, weights, maps and protocol hashes stayed frozen according to the original runner.

Four engineering games again demonstrated building33 before32, actual recruitment and conserved transfer of at least five creature types. Real transfers to the original hero were169/148/268/74. All eight NK games also passed mechanism coverage; recruitment/transfer alone did not solve strategic loss.

Three games consumed a passive native_battle_ready after terminal; the new v2 auditor required exactly one terminal and equal JSON values for every field except event. No other postterminal events are allowed. In other games, final victory/defeat closed the client before consuming the last transport-ready message, leaving one START without client END; this is recorded as terminal_unconsumed_battle_ready, not treated as an action failure. A supplemental initial assumption that START/END client counts must always match failed on the first terminal win; this diagnostic assumption was corrected without changing the registered strict acceptance or evidence. There is no unmatched movement action in any episode.

The raw legacy audit source before modification is preserved as `audit_supply_raw_before_terminal_tail.py` and in acceptance05b/source-snapshot. The v2 terminal rule passed8 meaningful tests: legal identical ready and terminal-only accepted; before_move, unknown event, ACK event, changed state, missing terminal and repeated terminal rejected. acceptance05/05b original failures remain unchanged.

Games and runner exited naturally. Shared pool release was announced to root and runner_audit; all further work here is read-only and does not reserve pool/GPU. Full evidence includes per-file SHA, line references and original native paths.
