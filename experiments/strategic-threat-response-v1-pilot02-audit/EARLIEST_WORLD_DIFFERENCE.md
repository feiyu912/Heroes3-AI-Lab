# Pair7: earliest divergence is an opponent task choice before Director acts

Read-only conclusion: the discordant train02blue seed2026101882 pair is **not an exact counterfactual of pressure-release behavior**. Inputs/source/runtime were correctly frozen, but the first recorded different opponent action precedes any Director policy action, every release, and every native battle. This limits causal attribution without invalidating the16 games' engineering legality audits.

EARLIEST_WORLD_DIFFERENCE.json preserves exact request SHA, numbered raw logs, opponent movement prefix and own trace. Client log SHA is also bound by AUDIT.json and per-episode RAW_AUDIT.json.

|Order|Baseline|Candidate|Meaning|
|---|---|---|---|
|NPC movement1,log8171|hero2,(7,10)→(7,9)|same|First two moves agree|
|NPC movement2,log8234|hero2,(7,9)→(7,8)|same|Hero exchange task then finishes|
|NK task selection,log8507|Explore(5,10)by red strategic hero,8tiles; displayed priority662.374|Explore(5,9)by Orrin,5tiles; displayed priority662.374|Different task at equal **printed** priority; full internal exact tie is not proven|
|NPC movement3,log8519|hero2,(7,9)→(6,10)|hero20,(7,8)→(6,9)|Different actual server-received hero/path, not just different candidate enumeration|
|Director first step|log9765|log9827|No Director step was issued before the NPC divergence|
|Director requests1..16|Exact request byte SHA equal|same|Own observable trajectory still agrees through sixteen actions|
|Own trace up to before_move17|84 records|same84records|No own army casualty/resource/movement-state difference in this prefix|
|Request17,day3|No visible enemy hero; chooses mine(23,20)via(29,16)|Sees240-value enemy hero(20,13); chooses it via(28,16)|First different Director observation and real movement; own army5114 in both|
|Candidate original hero removal|n/a|trace683,day15|Occurs before first release|
|Candidate first release|n/a|trace756,request155|Too late to directly cause this hero's earlier death|

Both logs contain **zero BattleStart/BattleResult/BattleStackAttacked/casualty events before log8519**. Therefore this earliest native world/path divergence is not an already different BattleAI combat roll or casualty result. The world has an opponent hero/task-order difference before the changed Director acts. The weak240-value enemy in request17 also cannot trigger the1.5×5114 pressure threshold.

The archived baseline Director only invokes findTarget through issueMove from the guarded own-turn scheduler. Its added ArmyDescriptor temporary in candidate findTarget thus has not executed when the red NPC's first-turn task choice already differs; that particular executed-allocation explanation cannot directly produce an earlier event. The recompilation/shared-library process layout can still differ before game start, and NPC task iteration/tie-breaking or scheduling may depend on it. Those are **hypotheses**, not established root causes; this audit did not change NPC code, inspect future RNG for policy use or run another game. Displayed662.374 alone is not proof that exact priorities are equal, nor is heap sensitivity proven by object addresses.

Observed full scores remain baseline3/8 and candidate2/8. The sole win→loss and its early hero death cannot honestly be labeled release-caused harm on this evidence. Conversely, no benefit was demonstrated, and A remains unapproved as default. Root has restored the accepted V8 source/binaries; future typed experiments should begin from archived e198 baseline, with A absent. All further work can read these preserved archives independently of temporary live probe sources.
