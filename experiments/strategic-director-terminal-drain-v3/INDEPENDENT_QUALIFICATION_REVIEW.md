# Independent qualification review

All three completed qualification games passed a fresh CPU-only run of v6 whole-game, v3 replan and the unchanged proxy auditors into `independent-qualification-01/`. The independent wrapper `review_qualification_raw.py` also checks raw registries without importing the registry parser. Original inputs, raw games, native source and original results were not modified. No native/GPU operation or optimizer update occurred in this review.

|Case|Normal exit|Owned policy moves / automatic EndTurn|All owned registrations = actual ACKs|Atomically cleared foreign waits|
|---|---:|---:|---:|---|
|hang-repro, blue vs NK|0|237 / 27|399|866, 867|
|Empty red control|0|117 / 12|192|none|
|Empty blue control|0|189 / 19|278|none|

These are engineering qualifications, not independent strategy gains. The NK reproduction is a genuine day28 blue defeat; the original killed timeout remains invalid/unscored.

## What the 399-request registry actually covers

The NK case has 264 strategy requests, plus 135 additional owned native requests. Its full exact-type breakdown is: 237 MoveHero,27 EndTurn,81 MakeAction,23 RecruitCreatures,20 ArrangeStacks,7 BuildStructure,2 QueryReply,1 SaveGame and1 AdvInterfaceReady. Every registration belongs to player1 and has exactly one unconditional actual ACK and one Director ACK with the same ID/player/native packet type and success1, in the required order. This is not a move-only registry; it includes battle, economy, query, save and interface-readiness requests.

The complete client stream contains867 unique request IDs and865 actual received ACK IDs. The remaining IDs are precisely866/867 from the atomic termination return. The ACK set plus cleared set accounts for every actual client-send ID. The cleared set has empty intersection with **all399** historical Director registration IDs, not just the final pending owned move. Both Empty cases account for all their request IDs by actual ACKs and clear no foreign wait.

Clearing a wait does not certify action non-execution. In particular,866 can already have been applied on the server while its ACK remains buffered;867 was the late peer move without an observed successful ACK. Neither is synthesized as ACKed, applied or successful, and neither becomes a policy sample.

## Exact reproduction and the strategy-trace difference

All237 original request files and all237 action files match byte-for-byte. `strategy-decisions.jsonl`, `strategy-trace.jsonl.targets.jsonl` and `strategy-trace.jsonl.replan.jsonl` also match byte-for-byte.

The complete strategy trace does **not** match byte-for-byte: the old timeout has1113 lines; the normal-exit reproduction has1112. The reproduction is an exact **byte prefix** of the original, ending at the same real `defeat` snapshot: day28, own-turn27, gold1000, wood84, ore86, no heroes and no towns. The old extra line1113 is solely `native_battle_ready`; all its other state fields equal the defeat snapshot. The new close completes before that queued terminal-tail readiness notification is consumed. There is no pre-terminal strategy/economy/action difference in this trace comparison, and no claim that both full trace files are identical.

## Evidence and limits

The fresh independent `AUDIT.json` records raw/source/output SHA, exact request/action file hashes and the original timeout status. Candidate manifest, actual compiled source manifest, source snapshots, actual loaded client/library identity, actual terminal state, real application/ACK contracts and exit0 are retained by the reaudited gates. The old failure was not rewritten or rescored.

This verifies three engineering cases and recorded reproduction projections. It does not prove complete hidden-world determinism, safe retreat, human tactics, higher win rate or readiness of a general multihero strategic AI. Subsequent paired evaluation remains separate.
