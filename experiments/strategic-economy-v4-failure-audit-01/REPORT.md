# Economy acceptance stopped: battle-end resume races with first level-up prompt

The four-EmptyAI engineering gate did not complete. First game (train01/red,
seed2026101860) passed full native/raw/engineering checks. Second game
(train01/blue,same seed) reached a native terminal but failed strict raw action
success. The supervisor wrote acceptance-01/EXECUTION.json status=failed and did
not start the remaining two engineering games or any Nullkiller2 development
games. No frozen input, source, policy, binary or prior report was modified.

## Verified economic mechanism in the valid first game

Original town12 built33 on day5: trace92(before_build)→93(successful ACK state),
then32 on day6: trace118→119. Actual recruitment and conserved town→hero transfer
both cover creature IDs0,2,4,6,8.169 troops were delivered to the original main
hero. The native game ended normally on day19, Director won, with no rejected
move/economy/query. This proves one engineering case, not all four and not
learned economics or comparative strategic improvement.

## Another query-resume path remains unsafe

Failed native directory:
`/root/heroes3-ai-lab/workers/adv-runs/economy-v4-engineering-map0-blue-2026101860-2026101860-fwugh6es`.

On day31, decision295 is a supplied single candidate: original hero1 from
(16,13,0) to enemy(17,12,0). Trace822 records before_move,823 records move_failed;
hero remains(16,13,0) with474 movement and army75 creature0,46 creature2,
12 creature6,25 creature4,12 creature8. This is not a policy out-of-range action.

Native log33349 receives BattleEnded. Server33362–33366 creates/sends a first
HeroLevelUp query334 after resolving the battle. Client33376, while still inside
BattleEnded handling, submits MoveHero484 before receiving that level-up prompt.
33395/33396 rejects it because query334 remains. Client33398 then receives
HeroLevelUp and33402 sends QueryReply485.33441 completes the upgrade and33472
reports successful QueryReply, but33477 already treats the failed move's hero
as blocked and ends the turn. Server's real PlayerBlocked解除 is only sent33459
and received33462, after movement/visit queries have popped. The present
battleEnded callback clears battleBusy and calls advanceTurn too soon; the
playerBlocked callback only sets busy on start and ignores the解除 event.

The previous queryResolved-only fix passed its exact chained-upgrade regression,
but does not cover the earlier BattleEnded→FIRST-upgrade-prompt transition.
This result narrows the remaining protocol defect; it does not invalidate the
prior controlled-prefix evidence. Another query346 rejection occurs later at
log35372/35390 and should be checked in the same corrected regression.

Do not relax the gate because final termination succeeded or increase training.
A new native variant should defer battle-end continuation until the native
query/movement block is actually released, and test upgraded/ordinary battle
paths before restarting the registered economy acceptance in a new directory.
The parent owns the native fix; this audit made no source changes or new games.

Evidence:

- client.log SHA0d69651fc3d6e3465d50130d47da1b985635f7d2104e1f7c1c7b95658a359fa9
- strategy-trace SHA45c01a45fd7d195adf50100a4fc27522304745f25591e9256b87d81bb0f2e5b5
- strategy-decisions SHA7a932d912b96885ffa55dd477c8e4eba6c9646fee131c1d3c4bdcb8cad7f1e9a

AUDIT.json contains the supplied request, exact trace states, original log
33316–33515 context, later rejection lines and verified unchanged protocol hashes.
BC eligibility0. The failed game is not counted as a valid policy win/loss or
as a passed economy acceptance case, even if some construction succeeded.
