# Native economy v4 engineering acceptance and fixed training-map development

This operational protocol supplements PLAN.md without changing it. No games
start until the parent announces compilation complete and supplies stable native
libvcmi.so/broker SHA. No training or GPU learner is instantiated.

Stage1: exactly4 engineering games, the two existing TRAIN maps (mines and the
file named development), Director red and blue, versus EmptyAI, seed2026101860.
Mode legacy-policy, frozen old continuous-2/update-2.pt SHA
f524796161915cb43ae9e228f13dd72c195df016ce5d2c25dab7d8a7d2aeb7cc.
This holds the learned target selector fixed while changing scripted economy.

Verify every game's original own Castle has a successful native building33
state transition before successful building32. Require at least3 creature types
actually recruited, verified by whole-own-army count increase and matching
available-recruit count decrease; require at least3 creature types actually
transferred, with troop conservation from town to hero and successful ACK.
Candidate recommendations, planned buildings and added units without native
transactions do not count. Zero economy_failed/move_failed, native request/file
consumption matched, no query rejection, QueryReply sends=successes.

All4 must pass those mechanism conditions before stage2. A native-valid game
that lacks development coverage is reported as engineering_gate_failed rather
than a fake illegal game; stage1 still finishes its four registered cases to
show coverage. Any technical invalid game stops immediately as status=failed.

Stage2: exactly8 train-map development games versus Nullkiller2: two TRAIN maps,
both Director colors, seeds2026101861 and2026101862, same mode/checkpoint/native.
Report native wins/losses, original main loss day/status, delivered troop counts,
and actual building/recruit/transfer records. Stage2 measures this fixed scripted
variant only, not a learned improvement or an independent comparison against the
old binary. No final-test/development-split map is played. Do not add games or
switch seeds after seeing unfavorable cells.

Freeze PLAN, this protocol, all used Python/native sources, native3 binaries,
native faction/config JSON, both map files, parent weights and broker/encoder
before the first game. Unique output directory refuses overwrite. Per-game
raw audit outputs preserve exact paths, line references and hashes; exception
records and partial logs remain. No input edits between games. Historical
visible-v3/query-only/native failures remain untouched. BC eligibility0.
