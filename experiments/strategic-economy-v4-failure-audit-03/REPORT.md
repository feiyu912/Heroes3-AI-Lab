# Economy engineering passes; first NK game exposes missing battle-end wakeup

Acceptance-03 completed all four registered EmptyAI engineering cases with
strict raw native verification. Every game built original Castle dwelling33
before32, recruited and conserved transfers of at least five actual creature
types, confirmed every movement including the last, and had no query, move or
economy rejection. All four native games were Director wins with original main
hero surviving. Building/recruitment remains scripted, with the old fixed model.

| TRAIN map / Director side |33→32 day|Actual recruited/transferred types|Troops to original main|Native days|
|---|---|---|---:|---:|
|mines/red|5→6|0,2,4,6,8|169|19|
|mines/blue|3→4|0,2,4,6,8|148|33|
|development-file/red|5→6|0,2,4,6,8,10|268|29|
|development-file/blue|3→4|0,2,4,6,8|74|15|

These four outcomes establish the registered engineering mechanism in both
TRAIN maps/roles. They do not establish learned economics, relative win-rate
improvement or a final-test result.

The first registered Nullkiller2 game (mines/red/seed2026101861) then timed out
at120 seconds, with no native terminal. Acceptance-03 status remains failed;
the game is invalid rather than a loss, and the other seven NK games were not
started. No frozen input was modified or failed outcome repurposed for training.

## Native failure chain

Directory:
`/root/heroes3-ai-lab/workers/adv-runs/economy-v4-nk-development-map0-red-2026101861-2026101861-nrs30b5a`.

Day6 issued44 real strategic requests. All44 have correct response hashes and
successful native move ACK states, as do44 movement blocked/unblocked pairs.
There is no move_failed or economy_failed. The last owned state still has
1136 movement and army34 creature0,19 creature2,4 creature6,7 creature4, plus
one town. Thus this is not missing policy response, absent army, exhausted
movement, an arbitrary loss or a need for more PPO samples.

Native hero-vs-hero battle query147 affects both players. Server log19238
first pops RED's battle query, then RED's visit146 at19245 and movement145
at19251; the Director receives movement unblock19258–19266. At that point
battleBusy still holds, so its advanceTurn returns. Server only then pops BLUE's
battle query19267, removes enemy hero86 and emits BattleEnded19294. Client
receives BattleEnded19308–19315 and clears battleBusy, but the current callback
does not advance. The only later ACK belongs to Nullkiller2 (19316–19321), not
an owned query/move. There is no further Director wakeup, and day6 never ends.

This is the complementary event order to the earlier neutral-battle upgrade
race. The movement/query-ACK guards correctly prevent premature action, but
removing all continuation from battleEnded loses a wakeup when movement has
already unblocked and no own QueryReply is pending. Restore a guarded wakeup
from battleEnded using the existing movementBusy/queryRequests gates, then
regress this timeout and the two earlier upgrade/terminal seeds. The parent
owns that native correction; this audit made no native changes or new runs.

AUDIT.json preserves final trace213, all44 request/action SHA bindings, exact
last battle ordering, native timeout/result, unchanged source/binary/map/model
freeze, and the four successful engineering audits. There are0 valid NK games,
0 NK losses and0 optimizer steps in this batch. BC eligibility remains0.
