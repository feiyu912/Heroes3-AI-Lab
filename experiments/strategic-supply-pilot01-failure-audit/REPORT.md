# Supply pilot stopped correctly: chained level-up query race

The registered16-game pilot did not complete. Ten games passed per-game raw
audits (five paired cells); game11 reached a native terminal but failed the
registered action-success gate. EXECUTION.json remains status=failed. Remaining
five games were not launched. No test, GPU training, frozen policy edit or gate
relaxation occurred. These are development/engineering records, BC eligibility0.

## Exact failure

Game: train02/red/seed2026101852/legacy-policy. Native directory:
`/root/heroes3-ai-lab/workers/adv-runs/supply-map1-red-2026101852-legacy-policy-2026101852-zmo6lhma`.

At day18, strategy-decisions line156 and public request156 choose legal candidate0:
hero2 at(11,30,0), destination(15,23,0), next(12,30,0), own army value6048,
visible target estimate2208. Trace384 records before_move; trace385 records
move_failed with position unchanged and1348 movement still available; trace386
then ends the turn.

Native log50272 submits that move;50273 identifies MoveHero request643. Before
its execution,50290–50291 state that RED must answer pending queries, with top
CHeroLevelUpDialogQuery401. Only50293 delivers HeroLevelUp to the client;
50297 submits QueryReply644. The move was already rejected.50335 records skill0
completion, but50339 reports no hero with movement points because the failed
move blocked that hero. The remaining1348 movement was not actually exhausted.
MOVEMENT_FAILURE.json preserves public request, exact decision and log contexts.

The registered native movement/ACK gate therefore caught a real scheduling
defect. This was not an illegal out-of-range policy choice, economy failure,
crash, hidden-information issue or supply override. Smoke/result passed native
terminal and file protocol; its failed_move_replies counter stayed0 because the
rejection occurred before a HeroMoved reply. The strict trace saw what that
legacy counter missed. Do not silently count the game as a valid policy sample.

Most likely mechanism: after an earlier query reply/visit transition, local
pendingQueries empties before the chained level-up query arrives. It is unsafe
to treat one QueryReply ACK as proof that the server query stack is drained.
The source's immediate advanceTurn then sends a MoveHero too early. A new native
version needs a query-drain scheduling fix and a targeted replay of this seed;
do not hide the failure by weakening the audit or changing the seed.

Failure evidence SHA:

- client.log: a1007c3afbec80b42fa7c06f1e69e790bc3c1eb1cea6824d1b8bbb4a88f6c35f
- strategy-trace.jsonl: d188a6d1358ed7bdcf08b43a3f0e3a1bfaf9f282cf836cb16c53ba1e1c3c572a

## Valid prefix: no differentiated behavior or benefit

All five completed pairs have identical full native strategy-state trace SHA,
winner, first-main-hero loss day and delivered troops. Both methods lost every
audited prefix game. The supply method made859 audited decisions,566 with one
candidate. It had99 decisions containing a supply option and selected no action
different from its baseline.66 decisions explicitly reported an already preferred
supply baseline. There were18 decisions whose baseline was not kind4 while a
supply choice existed; every one scored below the fixed0.60 dispatch threshold.
Thus lack of effect is not attributable solely to commitment; the rule's gate
also prevented all available alternative returns in this prefix.

Do not present zero paired difference as full-protocol evidence. This prefix
lacks the rest of train02 roles/seeds and is not an independent capability test.
A later dispatch hypothesis must keep these records and register fresh comparisons,
rather than lowering the threshold until these particular seeds look favorable.

## Separate confirmed construction dependency omission

The original four training-loss runs each contain their own runtime-copied
config/factions/castle.json. All four historical files have SHA
3b152491e0e19f75eb81e322b33dc4eb4719574d0e1ecbb484f765b8e54dfc9b.
They independently confirm dwellingLvl3 requires dwellingLvl4; dwellingLvl4
requires blacksmith and dwellingLvl1. The frozen Director priority lists include
DWELL_LVL1/2/3 but omit4–7 and upgrades. Hence the planner cannot unlock Castle
level3 on these starting towns, regardless of later resources. This conclusion
comes from historical run-local configs and frozen source snapshots, not merely
the current working tree. BUILDING_AUDIT.json binds exact lines, original source
SHA and daily own-town building lists; native faction config copies are preserved
in native-faction-config-snapshots/.

Original own town IDs12,13,18,19 only ever show dwelling IDs30/31 in all four
loss traces. Newly captured towns may inherit other buildings, so the finding
concerns construction of the starting Castle towns rather than claiming all
possible towns in the world are limited to two creature tiers. This structural
economic gap warrants a separate native version and development experiment;
extra PPO updates cannot add buildings absent from the script's action set.

FAILURE_AUDIT.json preserves unchanged registered input checks, prefix evidence
and failure state. PREFIX_DIAGNOSTIC.json records the exact comparable prefix
and public opportunity scores. No historical pilot output was overwritten.
