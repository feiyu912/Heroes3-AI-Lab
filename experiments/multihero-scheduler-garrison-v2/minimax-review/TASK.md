你是用户明确授权的独立 MiniMax 审核员。本任务通过本机 DeepSeek Harness 正常 headless CLI 委派，指定 provider mini / MiniMax-M3.1-Flash。你只收到下列明示源码和报告摘录，没有访问原始 native logs，也没有运行任何实验。所有工具已禁用；不得尝试调用工具、读写其他路径、编译、训练、运行 native/GPU、拿资源锁、修改 freeze、外部通信或委派。只根据提供的原始文本做独立技术审核，输出完整中文审核报告。
任务：审核 multihero-scheduler-probe-v1 工程停止原因以及 v2 garrison 方案的可识别性。请优先找实际致命缺陷，区分确定问题和需源码确认的风险，不要编造通过结果。v2 尚未原生运行，不能说通过。检查 cb->swapGarrisonHero 和 ACK 后条件是否确立真实 garrison；isGarrisoned/control移动负例是否会因原引擎本来禁止garrison move而不可识别；scheduler_selected 是否能辨认旧臂选择控制与新臂排除；现有审计需要哪些独立重算，ACK、地图一致性、资源和军队不变如何验证；单因素是否成立；提出最少而必要的预注册闸门。明确本文仅审核列出材料的完整文本，不是原始日志验证。
输出：1审核范围及局限 2按严重性列出问题（文件及函数/片段）3新旧臂可能结果的解释矩阵 4继续前必要修复 5只读结论（仍未资格化/待运行）。请别执行，也不要把这当成操作任务。


===== experiments/multihero-scheduler-probe-v1/NATIVE_RESULTS.md =====
# Scheduler probe: native results and engineering stop

## Run

- Evidence source: `/root/heroes3-ai-lab/evaluations/multihero-scheduler-probe-v1-01`
- Archived copy: `native-evidence-01/`
- Variant: `scheduler`
- Capsule:
  `/root/heroes3-ai-lab/evaluations/multihero-scheduler-capsule-01/scheduler`
- Server mode: native thread server (`useProcess: false`)
- Policy broker: absent
- Seed: `2026102501`
- Final test: not touched
- Training samples: 0
- Optimizer steps: 0

## Native observations

- `turn_open` count: 2
- successful `endturn_ack` count: 1
- controlled stop: true
- timeout: false
- loaded capsule identity: verified
- thread server gate: passed
- failed move ACKs: 0
- changed frozen inputs: 0

Successful mobile move sequences (request ids matched to `move_ack result=1`):

- hero 0: 12 successful sequences; turns 1 and 2; positions
  `(7,10) -> ... -> (17,12)`
- hero 2: 11 successful sequences; turns 1 and 2; positions
  `(10,10) -> ... -> (16,6)`

The scheduler therefore did move two independent owned heroes, and it did so
after a successful turn boundary. This is a mechanism observation only.

## Failure

The intended control hero 3 was not blocked or garrisoned. It was loaded as a
normal mobile own hero and moved from the town area through
`(7,9) ... (7,3)`. The audit found:

- `move_sent_for_non_mobile_hero` (10 occurrences)
- `successful_move_ack_for_non_mobile_hero` (10 occurrences)
- `town_tile_control_moved`
- `town_tile_control_scheduled`
- `native_log_scheduled_control_hero`

Audit result: `engineering_pass: false`.

This does **not** establish scheduler qualification. The fixture's control
condition was invalid. The run must not be described as a pass, and it is not a
win-rate or strategic-strength result.

## Raw hashes

- `probe.jsonl`:
  `25ea6914583c4b2ec2b58bfc29751c2d9e3f9964a41912eeadef50ffcb82acae`
- `strategy-trace.jsonl`:
  `0a6a4d3d42c451430b0c73dcec3eb8b6210d88fd0298b095e1ccb8ef7406ba46`
- `client.log`:
  `8365e92c034b91186773286e2ed9e2d29e2f9da3c08163450a8664eb9b9343d2`
- `plan.json`:
  `04978a018777b3eb3b660a0e9ed227f6d19284882f933948e38e486f290b3bad`
- `execution.json`:
  `4c5d1734be6c241ffb6cc56b7966d1ea51e883f0549dc979c7580aa6721850b7`
- `AUDIT_SCHEDULER.json`:
  `3cb5efcc20837e83e2612de54432d8d39269bba1a73fded656025ba7e0f0a17c`

The complete file hash table is in `native-evidence-01/ARCHIVE.json`.

## Engineering stop

Per the failure rule, the raw evidence and fixture are preserved. No silent
retry, reseed, or gate relaxation was performed. The next scheduler attempt must
be a new single-factor experiment with a genuinely blocked/garrisoned control,
or a source-derived scheduler change (for example, filtering
`CGHeroInstance::isGarrisoned()` in `pickHero`) followed by a legitimate control
fixture. PPO training and final-test work remain blocked until the scheduler
gate is actually qualified.


===== experiments/multihero-scheduler-probe-v1/SOURCE_REVIEW.md =====
# Scheduler source review

## Accepted scheduler

`/root/heroes3-ai-lab/src/vcmi-adv/AI/DirectorAI/CDirectorAI.cpp`

`CDirectorAI::pickHero`:

- filters by owner;
- skips heroes in `blockedHeroes`;
- chooses the owned hero with the greatest `movementPointsRemaining()`;
- does **not** check `CGHeroInstance::isGarrisoned()`.

`CDirectorAI::findTarget`:

- builds current-turn path information;
- scores visible enemy heroes, enemy towns, mines, own-town reinforcements,
  resources/pickups, and fog frontier;
- returns the selected candidate;
- external policy is only entered when `LAB_ADV_AGENT_DIR` is set.

The accepted `getHeroesInfo()` path returns the player's hero list without
filtering garrisoned heroes:
`lib/callback/CPlayerSpecificInfoCallback.cpp` (`getHeroesInfo`) returns
`playerState->getHeroes()`. The separate `getHeroSerial` has an
`includeGarrisoned` flag, but `getHeroesInfo` does not.

Therefore the original `pickHero` can see a garrisoned owned hero. Whether it
would have nonzero movement is an engine-state question; a real control fixture
would need to establish that, not assume it.

## What this run established

The third owned hero was placed on the town tile in the map object coordinates,
but it loaded as an ordinary mobile hero. It was not `isGarrisoned()` merely by
sharing the town tile. The scheduler selected it and the native engine applied
its moves. That is a fixture-control failure, not evidence that the scheduler
handles a true garrison correctly.

The two intended mobile heroes did receive successful native move ACKs across
two own turns. That observation is preserved but does not qualify the scheduler
because the control gate failed.

## Next source-derived options

1. Add `!hero->isGarrisoned()` (and, if required by the engine state, the
   appropriate visiting-town condition) to `pickHero`, then build a new
   isolated candidate and test a genuinely garrisoned control.
2. Or construct a genuinely blocked control (impassable-pocket/terrain or a
   runtime garrison setup) without changing scheduler semantics, and rerun the
   same gate.

These are separate single-factor experiments. Do not silently change the gate
or reuse the failed control fixture as if it had passed.


===== experiments/multihero-scheduler-probe-v1/ENGINEERING_STOP.json =====
{
  "status": "scheduler_probe_not_qualified",
  "reason": "intended town-tile control hero 3 was mobile and was scheduled",
  "engineering_pass": false,
  "raw_evidence": "/mnt/g/Heroes3-AI-Lab/experiments/multihero-scheduler-probe-v1/native-evidence-01",
  "source_evidence": "/root/heroes3-ai-lab/evaluations/multihero-scheduler-probe-v1-01",
  "raw_sha256": {
    "probe.jsonl": "25ea6914583c4b2ec2b58bfc29751c2d9e3f9964a41912eeadef50ffcb82acae",
    "strategy-trace.jsonl": "0a6a4d3d42c451430b0c73dcec3eb8b6210d88fd0298b095e1ccb8ef7406ba46",
    "client.log": "8365e92c034b91186773286e2ed9e2d29e2f9da3c08163450a8664eb9b9343d2",
    "plan.json": "04978a018777b3eb3b660a0e9ed227f6d19284882f933948e38e486f290b3bad",
    "execution.json": "4c5d1734be6c241ffb6cc56b7966d1ea51e883f0549dc979c7580aa6721850b7",
    "AUDIT_SCHEDULER.json": "3cb5efcc20837e83e2612de54432d8d39269bba1a73fded656025ba7e0f0a17c"
  },
  "observations": {
    "turn_open_count": 2,
    "mobile_heroes_with_successful_acks": [
      0,
      2
    ],
    "mobile_moves_observed_in_turns": [
      1,
      2
    ],
    "control_hero_3_scheduled": true,
    "failed_move_acks": 0
  },
  "next_step": "do not rerun silently; design a new fixture with a genuinely blocked or garrisoned control, or source-review and change the scheduler candidate to skip isGarrisoned heroes, as a new single-factor experiment"
}

===== experiments/multihero-scheduler-probe-v1/audit_scheduler.py =====
#!/usr/bin/env python3
"""Strict scheduler gate for the two-mobile-hero native probe.

This audit does not infer strength from movement. It only verifies that the
native Director scheduler issued and received successful move requests for both
owned mobile heroes, that the run crossed at least two own turns, that neither
the town-tile control nor another hero was scheduled, and that the loaded
library/thread configuration matches the plan. It writes AUDIT_SCHEDULER.json.
"""
import argparse
import hashlib
import json
from pathlib import Path

from capsule_support import thread_server_gate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_lines(path):
    rows = []
    for line in Path(path).read_text(errors="replace").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def positions(rows, hero_id):
    result = []
    for row in rows:
        for hero in row.get("heroes", []):
            if hero.get("id") == hero_id:
                position = (hero.get("x"), hero.get("y"), hero.get("z"))
                if position not in result:
                    result.append(position)
    return result


def audit(work: Path):
    work = Path(work)
    blockers = []
    plan = json.loads((work / "plan.json").read_text())
    execution = json.loads((work / "execution.json").read_text())
    probe_path = work / "probe.jsonl"
    trace_path = work / "strategy-trace.jsonl"
    log_path = work / "client.log"
    if not probe_path.is_file() or not trace_path.is_file() or not log_path.is_file():
        blockers.append("raw_evidence_missing")
        return {
            "engineering_pass": False,
            "blockers": blockers,
            "execution": execution,
        }

    probe = load_lines(probe_path)
    trace = load_lines(trace_path)
    log = log_path.read_text(errors="replace")

    # The plan hashes exactly the launched inputs; mutable live config is not
    # part of the frozen set. Any changed input invalidates the run.
    changed_inputs = []
    for path, expected in plan.get("hashes", {}).items():
        current = sha(path)
        if current != expected:
            changed_inputs.append({"path": path, "expected": expected, "actual": current})
    if changed_inputs:
        blockers.append("frozen_input_changed")

    if plan.get("policy_broker") is not False:
        blockers.append("policy_broker_not_disabled")
    if plan.get("settings_server_useProcess") is not False:
        blockers.append("server_process_mode_not_false")
    if not execution.get("controlled_stop"):
        blockers.append("native_stop_not_controlled")
    if execution.get("timed_out"):
        blockers.append("native_timeout")
    if execution.get("game_completed"):
        blockers.append("game_completed_unexpected")
    if not execution.get("loaded_library_verified"):
        blockers.append("loaded_capsule_identity_unverified")
    if execution.get("stop_reason") != "proved_two_mobile_heroes_move_ack":
        blockers.append("wrong_stop_reason")

    thread = execution.get("thread_server_verification", {})
    if not thread.get("passed") or thread.get("mode") != "thread":
        blockers.append("thread_server_gate_failed")
    try:
        recomputed_thread = thread_server_gate(
            execution.get("loaded_library_observations", []),
            log,
            plan.get("settings_server_useProcess"),
        )
    except AssertionError as error:
        recomputed_thread = {
            "passed": False,
            "mode": "thread",
            "error": str(error),
        }
    if not recomputed_thread.get("passed"):
        blockers.append("thread_server_recheck_failed")

    if not probe:
        blockers.append("empty_probe_log")
    for row in probe:
        if row.get("schema") != "multihero-scheduler-probe-v1":
            blockers.append("probe_schema_mismatch")
            break
        if row.get("variant") != "scheduler":
            blockers.append("probe_variant_mismatch")
            break

    turns = [
        (index, row)
        for index, row in enumerate(probe)
        if row.get("event") == "turn_open"
    ]
    endturn_acks = [
        (index, row)
        for index, row in enumerate(probe)
        if row.get("event") == "endturn_ack" and row.get("result") == 1
    ]
    if len(turns) < 2:
        blockers.append("fewer_than_two_own_turns")
    if not endturn_acks:
        blockers.append("no_successful_endturn_ack")
    if len(turns) >= 2 and not any(
        turns[0][0] < index < turns[1][0] for index, _ in endturn_acks
    ):
        blockers.append("no_successful_endturn_between_turns")

    sent = [
        row
        for row in probe
        if row.get("event") == "move_sent" and row.get("request_id") is not None
    ]
    acks = [row for row in probe if row.get("event") == "move_ack"]
    sent_by_hero = {}
    ack_by_request = {}
    failed_acks = []
    for row in sent:
        hero = row.get("hero")
        if hero not in (0, 2):
            blockers.append("move_sent_for_non_mobile_hero")
            continue
        sent_by_hero.setdefault(hero, []).append(row)
    for row in acks:
        hero = row.get("hero")
        if row.get("result") == 1 and hero not in (0, 2):
            blockers.append("successful_move_ack_for_non_mobile_hero")
        if row.get("result") != 1:
            failed_acks.append(row)
        key = (hero, row.get("request_id"))
        ack_by_request.setdefault(key, []).append(row)

    sequences = {}
    for hero in (0, 2):
        rows = sent_by_hero.get(hero, [])
        valid = []
        for row in rows:
            key = (hero, row.get("request_id"))
            matches = ack_by_request.get(key, [])
            if len(matches) == 1 and matches[0].get("result") == 1:
                valid.append(
                    {
                        "request_id": row.get("request_id"),
                        "own_turn": row.get("own_turn"),
                        "ack_turn": matches[0].get("own_turn"),
                    }
                )
            else:
                blockers.append("move_sent_without_one_successful_ack")
        sequences[str(hero)] = valid
    if not sequences.get("0"):
        blockers.append("mobile_hero_0_no_successful_move")
    if not sequences.get("2"):
        blockers.append("mobile_hero_2_no_successful_move")
    if failed_acks:
        blockers.append("move_ack_failure_present")

    ack_turns = {
        row.get("own_turn")
        for row in acks
        if row.get("hero") in (0, 2) and row.get("result") == 1
    }
    if len(ack_turns) < 2:
        blockers.append("mobile_moves_not_observed_in_two_turns")

    control_positions = positions(trace, 3)
    if len(control_positions) > 1:
        blockers.append("town_tile_control_moved")
    if any(row.get("event") == "move_sent" and row.get("hero") == 3 for row in probe):
        blockers.append("town_tile_control_scheduled")

    mobile_positions = {hero: positions(trace, hero) for hero in (0, 2)}
    for hero in (0, 2):
        if len(mobile_positions[hero]) < 2:
            blockers.append(f"mobile_hero_{hero}_position_not_changed")

    if "step hero 0" not in log:
        blockers.append("native_log_missing_step_hero_0")
    if "step hero 2" not in log:
        blockers.append("native_log_missing_step_hero_2")
    if "step hero 3" in log:
        blockers.append("native_log_scheduled_control_hero")
    if "external policy failed" in log:
        blockers.append("external_policy_path_entered")
    if "Got false in applying" in log or "has to answer queries" in log:
        blockers.append("native_query_or_apply_rejection")

    result = {
        "engineering_pass": not blockers,
        "blockers": blockers,
        "winner": None,
        "game_completed": False,
        "controlled_boundary": (
            "successful move_sent/move_ack for owned heroes 0 and 2 across "
            "two own turns; town-tile control not scheduled"
        ),
        "audit_gate": plan.get("audit_gate"),
        "mobile_heroes": [0, 2],
        "control_hero": 3,
        "mobile_move_sequences": sequences,
        "mobile_move_turns": sorted(
            turn for turn in ack_turns if turn is not None
        ),
        "mobile_positions": {
            str(hero): mobile_positions[hero] for hero in (0, 2)
        },
        "control_positions": control_positions,
        "turn_open_count": len(turns),
        "successful_endturn_ack_count": len(endturn_acks),
        "failed_move_acks": failed_acks,
        "changed_inputs": changed_inputs,
        "thread_server_verification": recomputed_thread,
        "training_samples": 0,
        "optimizer_steps": 0,
        "execution": execution,
        "raw_sha256": {
            "probe.jsonl": sha(probe_path),
            "strategy-trace.jsonl": sha(trace_path),
            "client.log": sha(log_path),
        },
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.work), indent=2))


===== experiments/multihero-scheduler-garrison-v2/common-setup.diff =====
--- preserved-v1
+++ garrison-common-setup
@@ -313,6 +313,9 @@
 		return false;
 	}
 
+    probeHero = hero->id.getNum();
+    traceState("scheduler_selection");
+    probeEvent("scheduler_selected");
 	int3 destination(-1, -1, -1);
 	std::string reason;
 	if(!findTarget(hero, destination, reason))
@@ -401,6 +404,12 @@
 	if(!turnActive || endingTurn || pendingMove || pendingEconomy || battleBusy || movementBusy ||
 		!pendingQueries.empty() || !queryRequests.empty())
 		return;
+    if(!garrisonSetupDone)
+    {
+        if(garrisonSetupPending) return;
+        setupGarrisonControl();
+        return;
+    }
 	if(issueEconomy())
 		return;
 	if(!issueMove())
@@ -435,6 +444,24 @@
 
 void CDirectorAI::requestRealized(PackageApplied * pa)
 {
+    if(pa->player == playerID && pa->packType == CTypeList::getInstance().getTypeID<GarrisonHeroSwap>(nullptr))
+    {
+        if(!garrisonSetupPending || static_cast<int>(pa->requestID) != garrisonSetupRequest)
+            throw std::runtime_error("Garrison setup ACK tuple mismatch");
+        const auto * town = cb->getTown(ObjectInstanceID(garrisonSetupTown));
+        const auto * hero = cb->getHero(ObjectInstanceID(3));
+        traceState("garrison_setup_ack_state");
+        const bool verified = pa->result && town && hero && hero->getOwner() == playerID &&
+            town->getOwner() == playerID && town->getGarrisonHero() == hero &&
+            town->getVisitingHero() == nullptr && hero->isGarrisoned() &&
+            hero->getVisitedTown() == town && hero->movementPointsRemaining() > 0;
+        probeEvent("garrison_setup_ack", static_cast<int>(pa->requestID), verified ? 1 : 0);
+        if(!verified) throw std::runtime_error("Garrison setup lacks real positive-MP garrison state");
+        garrisonSetupPending = false;
+        garrisonSetupDone = true;
+        advanceTurn();
+        return;
+    }
     if(pa->player == playerID && pa->packType == CTypeList::getInstance().getTypeID<MoveHero>(nullptr))
         probeEvent("move_ack", static_cast<int>(pa->requestID), pa->result);
     if(pa->player == playerID && probeTransferPending && static_cast<int>(pa->requestID) == probeTransferRequest)
@@ -503,6 +530,14 @@
 
 void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)
 {
+    if(const auto * swap = dynamic_cast<const GarrisonHeroSwap *>(pack))
+    {
+        if(!garrisonSetupPending || garrisonSetupRequest != -1 ||
+           swap->tid.getNum() != garrisonSetupTown || pack->player != playerID || requestID < 1)
+            throw std::runtime_error("Garrison setup request tuple mismatch");
+        garrisonSetupRequest = requestID;
+        probeEvent("garrison_setup_sent", requestID);
+    }
     if(dynamic_cast<const MoveHero *>(pack)) probeEvent("move_sent", requestID, -1);
     if(dynamic_cast<const EndTurn *>(pack)) probeEvent("endturn_sent", requestID, -1);
     if(probeTransferPending && dynamic_cast<const ArrangeStacks *>(pack))
@@ -560,6 +595,28 @@
 		traceState(result.victory() ? "victory" : "defeat");
 		turnActive = false;
 	}
+}
+
+
+bool CDirectorAI::setupGarrisonControl()
+{
+    const auto * hero = cb->getHero(ObjectInstanceID(3));
+    if(!hero || hero->getOwner() != playerID || hero->isGarrisoned())
+        throw std::runtime_error("Garrison fixture requires an actual owned visitor hero3");
+    for(const auto * town : cb->getTownsInfo())
+    {
+        if(town->getOwner() != playerID || town->getVisitingHero() != hero) continue;
+        if(town->getGarrisonHero() || hero->getVisitedTown() != town)
+            throw std::runtime_error("Garrison fixture town identity mismatch");
+        garrisonSetupTown = town->id.getNum();
+        garrisonSetupPending = true;
+        probeHero = 3;
+        traceState("garrison_setup_before");
+        probeEvent("garrison_setup_requested");
+        cb->swapGarrisonHero(town);
+        return true;
+    }
+    throw std::runtime_error("Fixture hero3 is not a real town visitor");
 }
 
 bool CDirectorAI::issueEconomy()
@@ -575,7 +632,15 @@
 		<< ",\"day\":" << cb->getCalendar().getCurrentDay()
 		<< ",\"own_turn\":" << ownTurns << ",\"gold\":" << cb->getResourceAmount(GameResID::GOLD)
 		<< ",\"wood\":" << cb->getResourceAmount(GameResID::WOOD)
-		<< ",\"ore\":" << cb->getResourceAmount(GameResID::ORE) << ",\"heroes\":[";
+		<< ",\"ore\":" << cb->getResourceAmount(GameResID::ORE) << ",\"resources\":[";
+    bool firstResource = true;
+    for(auto res : {GameResID::WOOD, GameResID::MERCURY, GameResID::ORE, GameResID::SULFUR, GameResID::CRYSTAL, GameResID::GEMS, GameResID::GOLD})
+    {
+        if(!firstResource) out << ',';
+        firstResource = false;
+        out << cb->getResourceAmount(res);
+    }
+    out << "],\"heroes\":[";
 	bool first = true;
 	for(const auto * hero : cb->getHeroesInfo())
 	{
@@ -583,7 +648,10 @@
 		first = false;
 		out << "{\"id\":" << hero->id.getNum() << ",\"x\":" << hero->visitablePos().x
 			<< ",\"y\":" << hero->visitablePos().y << ",\"z\":" << hero->visitablePos().z
-			<< ",\"movement\":" << hero->movementPointsRemaining() << ",\"army\":[";
+			<< ",\"owner\":" << hero->getOwner().getNum()
+            << ",\"garrisoned\":" << (hero->isGarrisoned() ? "true" : "false")
+            << ",\"town_id\":" << (hero->getVisitedTown() ? hero->getVisitedTown()->id.getNum() : -1)
+            << ",\"movement\":" << hero->movementPointsRemaining() << ",\"army\":[";
 		bool firstStack = true;
 		for(const auto & slot : hero->Slots())
 		{
@@ -599,7 +667,12 @@
 	{
 		if(!first) out << ',';
 		first = false;
-		out << "{\"id\":" << town->id.getNum() << ",\"buildings\":[";
+		out << "{\"id\":" << town->id.getNum()
+            << ",\"owner\":" << town->getOwner().getNum()
+            << ",\"visitor_id\":" << (town->getVisitingHero() ? town->getVisitingHero()->id.getNum() : -1)
+            << ",\"garrison_id\":" << (town->getGarrisonHero() ? town->getGarrisonHero()->id.getNum() : -1)
+            << ",\"upper_army_id\":" << town->getUpperArmy()->id.getNum()
+            << ",\"buildings\":[";
 		bool firstBuilding = true;
 		for(int b = 0; b < 44; ++b)
 			if(town->hasBuilt(BuildingID(b)))
@@ -686,7 +759,7 @@
     const char * path = std::getenv("LAB_HERO_PROBE_LOG");
     if(!path) return;
     std::ofstream out(path, std::ios::app);
-    out << "{\"schema\":\"multihero-scheduler-probe-v1\",\"variant\":\"scheduler\",\"event\":\"" << event
+    out << "{\"schema\":\"multihero-scheduler-garrison-v2\",\"variant\":\"garrison-v2\",\"event\":\"" << event
         << "\",\"request_id\":" << request << ",\"result\":" << result
         << ",\"query_id\":" << probeQuery.getNum() << ",\"pending_move\":" << pendingMove
         << ",\"pending_queries\":" << pendingQueries.size() << ",\"query_requests\":" << queryRequests.size()


===== experiments/multihero-scheduler-garrison-v2/single-factor.diff =====
--- baseline
+++ filtered
@@ -86,7 +86,7 @@
 	int bestMovement = 0;
 	for(const auto * hero : heroes)
 	{
-		if(!hero || hero->getOwner() != playerID || blockedHeroes.count(hero->id.getNum()))
+		if(!hero || hero->getOwner() != playerID || hero->isGarrisoned() || blockedHeroes.count(hero->id.getNum()))
 			continue;
 		const int movement = hero->movementPointsRemaining();
 		if(movement > bestMovement)


===== experiments/multihero-scheduler-garrison-v2/derive.py =====
"""Isolate a real server garrison setup and one scheduler eligibility change."""
import difflib,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'multihero-scheduler-probe-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,(a[:100],s.count(a))
    return s.replace(a,b,1)
def main():
    source=(OLD/'candidates/scheduler/CDirectorAI.cpp').read_text()
    header=(OLD/'candidates/scheduler/CDirectorAI.h').read_text()
    original=source
    header=once(header,'int probeHero = -1;', '''int probeHero = -1;
    bool garrisonSetupPending = false, garrisonSetupDone = false;
    int garrisonSetupRequest = -1, garrisonSetupTown = -1;
    bool setupGarrisonControl();''')
    source=once(source,'\tif(issueEconomy())', '''    if(!garrisonSetupDone)
    {
        if(garrisonSetupPending) return;
        setupGarrisonControl();
        return;
    }
\tif(issueEconomy())''')
    source=once(source,'\tint3 destination(-1, -1, -1);', '''    probeHero = hero->id.getNum();
    traceState("scheduler_selection");
    probeEvent("scheduler_selected");
\tint3 destination(-1, -1, -1);''')
    source=once(source,'void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)\n{', '''void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)
{
    if(const auto * swap = dynamic_cast<const GarrisonHeroSwap *>(pack))
    {
        if(!garrisonSetupPending || garrisonSetupRequest != -1 ||
           swap->tid.getNum() != garrisonSetupTown || pack->player != playerID || requestID < 1)
            throw std::runtime_error("Garrison setup request tuple mismatch");
        garrisonSetupRequest = requestID;
        probeEvent("garrison_setup_sent", requestID);
    }''')
    source=once(source,'void CDirectorAI::requestRealized(PackageApplied * pa)\n{', '''void CDirectorAI::requestRealized(PackageApplied * pa)
{
    if(pa->player == playerID && pa->packType == CTypeList::getInstance().getTypeID<GarrisonHeroSwap>(nullptr))
    {
        if(!garrisonSetupPending || static_cast<int>(pa->requestID) != garrisonSetupRequest)
            throw std::runtime_error("Garrison setup ACK tuple mismatch");
        const auto * town = cb->getTown(ObjectInstanceID(garrisonSetupTown));
        const auto * hero = cb->getHero(ObjectInstanceID(3));
        traceState("garrison_setup_ack_state");
        const bool verified = pa->result && town && hero && hero->getOwner() == playerID &&
            town->getOwner() == playerID && town->getGarrisonHero() == hero &&
            town->getVisitingHero() == nullptr && hero->isGarrisoned() &&
            hero->getVisitedTown() == town && hero->movementPointsRemaining() > 0;
        probeEvent("garrison_setup_ack", static_cast<int>(pa->requestID), verified ? 1 : 0);
        if(!verified) throw std::runtime_error("Garrison setup lacks real positive-MP garrison state");
        garrisonSetupPending = false;
        garrisonSetupDone = true;
        advanceTurn();
        return;
    }''')
    setup='''
bool CDirectorAI::setupGarrisonControl()
{
    const auto * hero = cb->getHero(ObjectInstanceID(3));
    if(!hero || hero->getOwner() != playerID || hero->isGarrisoned())
        throw std::runtime_error("Garrison fixture requires an actual owned visitor hero3");
    for(const auto * town : cb->getTownsInfo())
    {
        if(town->getOwner() != playerID || town->getVisitingHero() != hero) continue;
        if(town->getGarrisonHero() || hero->getVisitedTown() != town)
            throw std::runtime_error("Garrison fixture town identity mismatch");
        garrisonSetupTown = town->id.getNum();
        garrisonSetupPending = true;
        probeHero = 3;
        traceState("garrison_setup_before");
        probeEvent("garrison_setup_requested");
        cb->swapGarrisonHero(town);
        return true;
    }
    throw std::runtime_error("Fixture hero3 is not a real town visitor");
}

'''
    source=once(source,'bool CDirectorAI::issueEconomy()',setup+'bool CDirectorAI::issueEconomy()')
    source=once(source,'<< ",\\"ore\\":" << cb->getResourceAmount(GameResID::ORE) << ",\\"heroes\\":[";', '''<< ",\\"ore\\":" << cb->getResourceAmount(GameResID::ORE) << ",\\"resources\\":[";
    bool firstResource = true;
    for(auto res : {GameResID::WOOD, GameResID::MERCURY, GameResID::ORE, GameResID::SULFUR, GameResID::CRYSTAL, GameResID::GEMS, GameResID::GOLD})
    {
        if(!firstResource) out << ',';
        firstResource = false;
        out << cb->getResourceAmount(res);
    }
    out << "],\\"heroes\\":[";''')
    source=once(source,'<< ",\\"movement\\":" << hero->movementPointsRemaining() << ",\\"army\\":[";', '''<< ",\\"owner\\":" << hero->getOwner().getNum()
            << ",\\"garrisoned\\":" << (hero->isGarrisoned() ? "true" : "false")
            << ",\\"town_id\\":" << (hero->getVisitedTown() ? hero->getVisitedTown()->id.getNum() : -1)
            << ",\\"movement\\":" << hero->movementPointsRemaining() << ",\\"army\\":[";''')
    source=once(source,'<< town->id.getNum() << ",\\"buildings\\":[";', '''<< town->id.getNum()
            << ",\\"owner\\":" << town->getOwner().getNum()
            << ",\\"visitor_id\\":" << (town->getVisitingHero() ? town->getVisitingHero()->id.getNum() : -1)
            << ",\\"garrison_id\\":" << (town->getGarrisonHero() ? town->getGarrisonHero()->id.getNum() : -1)
            << ",\\"upper_army_id\\":" << town->getUpperArmy()->id.getNum()
            << ",\\"buildings\\":[";''')
    source=source.replace('multihero-scheduler-probe-v1','multihero-scheduler-garrison-v2')
    source=once(source,'\\"variant\\":\\"scheduler\\"','\\"variant\\":\\"garrison-v2\\"')
    baseline=source
    filtered=once(baseline,'hero->getOwner() != playerID || blockedHeroes.count(hero->id.getNum())',
                  'hero->getOwner() != playerID || hero->isGarrisoned() || blockedHeroes.count(hero->id.getNum())')
    for arm,cpp in [('baseline',baseline),('filtered',filtered)]:
        p=HERE/'candidates'/arm;p.mkdir(parents=True,exist_ok=True)
        for name,data in [('CDirectorAI.cpp',cpp),('CDirectorAI.h',header)]:
            target=p/name
            if target.exists():assert target.read_text()==data,'Preserve differing candidate'
            else:target.write_text(data)
    shutil.copy2(OLD/'capsule_support.py',HERE/'capsule_support.py')
    build=(OLD/'build_scheduler.py').read_text().replace("VARIANTS=('scheduler',)","VARIANTS=('baseline','filtered')")
    assert build.count("str(build_tree),'-v'")==2
    build=build.replace("str(build_tree),'-v'","str(build_tree),'-j4','-v'")
    (HERE/'build_scheduler.py').write_text(build)
    shutil.copy2(OLD/'fixture-01.vmap',HERE/'fixture-02.vmap')
    assert sha(HERE/'fixture-02.vmap')==sha(OLD/'fixture-01.vmap')
    (HERE/'common-setup.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),baseline.splitlines(True),fromfile='preserved-v1',tofile='garrison-common-setup')))
    (HERE/'single-factor.diff').write_text(''.join(difflib.unified_diff(baseline.splitlines(True),filtered.splitlines(True),fromfile='baseline',tofile='filtered')))
    (HERE/'DERIVATION.json').write_text(json.dumps(dict(passed=True,parent_cpp_sha256=sha(OLD/'candidates/scheduler/CDirectorAI.cpp'),
        fixture_map_sha256=sha(HERE/'fixture-02.vmap'),fixture_semantics='Unchanged map bytes plus actual GarrisonHeroSwap before any scheduling, positive-MP postnative garrison required',
        candidate_sha256={a:{n:sha(HERE/'candidates'/a/n) for n in ['CDirectorAI.cpp','CDirectorAI.h']} for a in ['baseline','filtered']},
        factor='Only eligibility hero->isGarrisoned() rejection; setup/instrumentation/fixture identical',native_runs=0,optimizer_steps=0),indent=2)+'\n')
    print('Derived two isolated candidates, exactly one scheduler predicate differs')
if __name__=='__main__':main()
