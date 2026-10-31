# Isolated adventure battle readiness barrier

`install.py` targets only `/root/heroes3-ai-lab/src/vcmi-adv`; run it before
`adv-install-ai.py` and the isolated CMake/Ninja build. It preserves each original
server source in `source-before/`, checks exact unique anchors, is idempotent, and
records installed source hashes. The original frozen battle build is unaffected.

Why: native movement unblock may precede or follow `BattleEnded`; neither callback
alone certifies that deferred visits, level-up prompts and victory checks have
finished. Waking on either caused a demonstrated deadlock or unexecuted terminal
action. Those failed experiments remain in economy acceptance-03/04.

At battle engagement the server records each participating player. At the end of
`handleReceivedPack`, after applying the entire request and sending its ACK, it
emits the existing `PlayerBlocked::UPCOMING_BATTLE / BLOCKADE_ENDED` only for players
whose query stack is empty and who have no current battle. Other players remain
registered until a later request closes their outstanding queries. DirectorAI
clears its battle barrier only on this explicit signal. Movement/query/ACK guards
remain conjunctive. Native `BattleEnded` is observation only.

This changes notification scheduling, not game rules, legal actions, combat,
resources, victory checks or rewards. Nullkiller2 ignores the added END signal
(its handler reacts only to START); other interfaces must be reviewed before
using this isolated protocol outside the lab. Readiness state is transient and
is not serialized: current recovery claims cover turn-start saves without active
battles, not arbitrary battle or action boundaries.

Compilation is an engineering check. Real acceptance and strict per-action
execution audits must pass before any new training data is admitted.
