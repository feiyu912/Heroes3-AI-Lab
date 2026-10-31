# Query-drain native regression: targeted defect reproduced and absent after fix

Independent read-only audit of the parent-run query-only regression, same failed
TRAIN map02/red/seed2026101852, same old learned checkpoint and legacy argmax.
No new game, training, test access or source edit was performed by this audit.

The earlier failure is preserved in strategic-supply-pilot01-failure-audit/.
New native directory:
`/root/heroes3-ai-lab/workers/adv-runs/query-drain-regression-01-2026101852-ouemas9p`.

## Controlled prefix and narrow source change

Requests1–156 are byte-SHA identical between the failed run and regression;
all156 emitted actions are byte-identical too. The exact formerly rejected
decision156 targets(15,23,0) via next(12,30,0) from(11,30,0). Checkpoint SHA and
broker/model/encoder sources are identical. Frozen native source diff shows one
behavior change: queryResolved erases the ID but no longer calls advanceTurn.
The extra two lines explain why QueryReply ACK resumes after chained prompts.
This is a controlled regression of the actual failed prefix, not merely another
game with the same final winner.

## Corrected native ordering and continued movement

Old log50290/50317 rejected movement because level-up query401 was still pending.
In the regression, log50276 receives HeroLevelUp;50282 sends QueryReply643;
50301 completes the level-up;50335 reports QueryReply successfully applied;
only50342 then submits the formerly rejected next movement. Thus the new move
follows the chained dialogue and successful reply, rather than preceding it.

Old trace385 was move_failed, still(11,30,0),1348 movement. New trace385 is
move_applied,(12,30,0),1198 movement. New trace387 continues to(13,30,0),1048.
The day18 turn finally ends at trace400,(15,25,0),0 movement. The1348 remaining
points were genuinely consumed through additional native moves, not hidden by
an early end-turn or synthetic success.

Across the complete new game:249 decisions have matched public request/action/
native consumption; no move_failed or economy_failed state exists. All15 native
QueryReply submissions have15 successful-application messages and no failure
or must-answer-query rejection. The independent episode audit verifies native
terminal, all input/request/action hashes, legal selection, actual transfer
conservation and main-hero removal evidence. RAW_AUDIT.json passed before any
later economic-native version was edited.

The regression still loses. Original main hero is natively removed by day23,
and delivered troops are192 total,146 to the original main. These are observed
outcomes and side effects, not evidence of general strategic improvement. The
query fix passes this one targeted regression; it does not prove every possible
dialogue/ACK sequence is race-free, and it does not repair the separate Castle
dwelling dependency omission.

## Evidence

COMPARISON.json records all156 old/new request SHA pairs, action SHA, exact native
source diff, old/new logs and query counts, and day18 move states. New strategy
trace SHA is d587475c6805c483394753e0e51d5b07377b4d5d95508c21e7f1cf266d802d85.
RAW_AUDIT.json binds complete249-decision evidence and transfer windows. Files
are new, old failure evidence remains unchanged. BC eligibility stays0 and no
model was promoted.
