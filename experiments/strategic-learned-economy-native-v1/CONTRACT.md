# Learned build native pilot — contract v1

Status: implementation contract, not native qualification. Frozen parent: terminal-drain-v3 candidate / qualified capsule03, nine payload files. New flag: `LAB_ADV_LEARNED_ECONOMY=build_v1`; unset means the original strict schema4 behavior. Any other value fails closed. New epoch: `learned-economy-build-v1`. No efficiency reward; native win +1 / loss -1 and original PPO remain the learning contract. Exactly one actual owned hero is required for policy requests; zero-hero rescue hire remains scripted, multiple heroes fail closed. No native save/control hydration support is introduced.

## Request and response

In the explicit new mode requests use `schema: "strategy-candidates-v5"`, `economy_epoch: "learned-economy-build-v1"`, and boolean `economy_window_open`. Existing request_id/player/hero/own_turn/own_hero_count/day/from/movement/own_army_value/visible_threats retain their actual meanings. Hero is the real single owned hero and is **context only** for build: its location is not a build destination. Existing top-level gold/wood/ore remain exact aliases of the corresponding new resource entries for migration of movement features.

Seven-resource objects `resources` and build `cost` have exactly these keys, integer nonnegative values: **wood, mercury, ore, sulfur, crystal, gems, gold**. This is also the numeric feature order, matching GameResID indices 0..6. JSON key order is not semantic; no seventh special/mithril resource is included. No invented affordability or prices: cost comes from the actual town building definition and eligibility from native canBuildStructure == ALLOWED.

`own_towns` retain position/army_value and add `town_id` (actual instance ID), `faction_id` (actual faction ID), `built_today` (native town built counter), and `buildings` (sorted actual building IDs). Only own towns are included. There is no hidden-state or enemy economic observation.

Candidate union:

```json
{"op":"move","kind":3,"position":[9,11,0],"next":[7,10,0],"path_cost":0.2,"heuristic_score":3.0}
{"op":"end_turn"}
{"op":"build","actor":"player_town","town_id":3,"building_id":11,"category":"income","cost":{"wood":0,"mercury":0,"ore":0,"sulfur":0,"crystal":0,"gems":0,"gold":2500}}
```

Build candidate keys are exactly op/actor/town_id/building_id/category/cost. **No position/next/path fields.** IDs are binding identities, not continuous semantic features. Category enum: `income` for TOWN_HALL/CITY_HALL/CAPITOL, `dwelling` for dwelling IDs, `infrastructure` for remaining ordinary buildings in the bounded existing priority set or ordinary prerequisite candidates. No Grail, BUILD_AUTO, BUILD_SPECIAL or BUILD_GRAIL request. Deduplicate town/building pairs; stable order is town ID then building ID. Ordinary preconditions, prerequisites, resource affordability, daily limits and ownership are enforced by native ALLOWED, not a second economic simulator.

Response remains the exact flat nine-key format selected_index/decision_id/player/hero/own_turn/op/request_sha256/classification/schema, but the new mode requires **`schema: "strategy-typed-action-response-v2"`**. The old mode continues to require response-v1 and schema4. `op` must equal the selected exact candidate, classification new_policy or diagnostic_only as before. The SHA binds exact request bytes. Build actor/subject/cost come from that immutable selected candidate, not free response parameters.

## Selection window and execution

Each actual own turn opens one window before optional scripted spending. On the first clean policy request offer legal builds together with existing legal movement candidates and genuine EndTurn. Zero legal moves still permits build/EndTurn using the actual hero context. Choosing move or EndTurn closes the window; choosing build closes it and permits at most one policy build that turn. There is no synthetic skip-build step. After the selected real native action ACK, preserve existing scripted recruitment/army transfer/rescue hire and subsequent movement decisions. **This mode never falls back to scripted building.** Existing schema4 remains unchanged. Zero-hero rescue cannot consume a fake policy decision.

Build uses the same unique prepared/outstanding policy tuple as MoveHero/EndTurn, with immutable actual player/hero-context/own-turn/decision/index/requestSHA/candidate and real native request ID, plus town/building. It cannot also use pendingEconomy. Recheck own town, ordinary definition, exact cost and ALLOWED before dispatch; a stale/rejected action fails closed. requestSent must verify actual BuildStructure pack player/requestID/tid/bid before binding. Only the matching successful real PackageApplied closes this transaction; buildChanged/resources callbacks are observations, not substitute ACKs. Existing late EndTurn ACK, query, movement, battle and terminal owned-request drain semantics remain intact.

## Audit observations

The original DirectorTypedEvent JSON file/client mirror is retained; build extends its policy event op/pack_type to build/BuildStructure and adds actual actor/town_id/building_id. native_action_sent includes actual request payload and pre-build resource/building snapshot. build_changed and build_ack_state observations record actual own-town buildings and all seven resources. Server logs actual BuildStructure identity/payload and actual visitor success with the same native request ID; client logs actual received NewStructures/SetResources payload, not inferred state changes. These new observations are qualification inputs for a new strict auditor; the old schema4 auditor must continue rejecting build.

Success requires selected candidate → real same-ID send payload → actual server application → actual NewStructures containing requested building / resource changes → real same-ID successful ACK, with query/terminal barriers drained. Automatic added buildings are allowed only as explicitly observed actual payload; do not require exactly one added building. The server may run follow-up effects; a resource delta with unexplained concurrent effects is not silently certified. File/client JSON observations must be identical. No fake ACK, remote build proxy, movement result or PPO step for scheduler/economy script work.

## Frozen scope

This candidate changes native generation/dispatch and evidence only. Python encoder/model/raw/admission training integration is a separate implementation bound to this contract and a new source/epoch; no old schema4 gate is relaxed. Native builds/runs/GPU are root-owned. Default builder behavior must be plan-only; original accepted binaries/source and all previous capsules remain immutable.
