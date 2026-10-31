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
