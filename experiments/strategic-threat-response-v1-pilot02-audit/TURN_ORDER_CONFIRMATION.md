# Extra check: NPC divergence precedes Director's first own turn

To exclude a findTarget-before-step scheduling ambiguity, the original raw logs were re-read around turn ownership. At NPC task divergence8507 and move8519, red's first turn is still running. Baseline only logs `Server ends turn of red` at9618 and Director's first build at9631; candidate logs those at9680 and9693. First Director step follows at9765/9827 after its initial three economic ACKs. Director initialization at7717 merely installs the interface, and the archived e198 source only calls findTarget from the guarded own-turn issueMove path.

Thus the new ArmyDescriptor construction inside candidate findTarget has not run when the opponent's first-turn task selection diverges. This rules out its *executed temporary allocation* directly causing that earlier selection. It does not rule out compile/load/process-layout effects, or independently unstable NPC scheduling/iteration. No such broader mechanism has been experimentally proven.

The raw log prefixes before8519 contain no BattleStart, BattleResult, BattleStackAttacked or casualty records in either arm. This is an opponent task/path choice before battle, not a pre-existing different BattleAI damage outcome. The evidence is an actual server MoveHero receiver line, so the effect is not confined to own candidate enumeration.

The underlying client.log SHA and complete numbered context are preserved by EARLIEST_WORLD_DIFFERENCE.json and the original per-episode RAW_AUDIT.json. No simulation was started to obtain this clarification.
