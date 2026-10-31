#!/usr/bin/env python3
"""Strict source-derived raw gate for the hero-exchange close/transfer probe.

v2 correction: CGarrisonDialogQuery does not send QueryResolved, so the gate
uses the successful QueryReply PackageApplied plus a later successful EndTurn
ACK. It never rewrites raw logs; it writes AUDIT_V2.json.
"""
from collections import Counter
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = HERE.parent / "multihero-mechanism-probe-v1"
sys.path.insert(0, str(V1))
from capsule_support import thread_server_gate


def load_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def army(state, hero):
    row = next(row for row in state["heroes"] if row["id"] == hero)
    counts = Counter()
    for creature, count in row["army"]:
        assert isinstance(count, int) and count > 0
        counts[creature] += count
    return counts


def one(events, name):
    found = [(i, row) for i, row in enumerate(events) if row["event"] == name]
    assert len(found) == 1, f"Exactly one {name} required, got {len(found)}"
    return found[0]


def gate(events, trace, log, variant):
    callback_i, callback = one(events, "exchange_callback")
    assert callback["courier"] != callback["receiver"] and callback["query_id"] >= 0

    issued = [row for row in events if row["event"] == "move_sent"]
    applied = [row for row in events if row["event"] == "move_ack"]
    assert issued and len({row["request_id"] for row in issued}) == len(issued)
    steps = re.findall(
        r"DirectorAI: step hero (\d+) (\([^\n]+?\)) -> (\([^\n]+?\)) "
        r"reason=PURE_ENGINEERING_actual_owned_hero_meeting",
        log,
    )
    assert len(steps) == len(issued) and all(start != end for _, start, end in steps), (
        "Real distinct-position MoveHero evidence required"
    )
    assert all(int(hero) == callback["courier"] for hero, _, _ in steps)

    before = next(row for row in trace if row["event"] == "probe_before_exchange")
    receiver_state = next(h for h in before["heroes"] if h["id"] == callback["receiver"])
    final_target = tuple(int(n) for n in re.findall(r"-?\d+", steps[-1][2]))
    assert final_target == (receiver_state["x"], receiver_state["y"], receiver_state["z"]), (
        "Move must really target the other hero tile"
    )
    assert "visits " in log, "Native object visit evidence required"
    assert not any(row["event"] in ("victory", "defeat") for row in trace), (
        "This probe must not claim a terminal game"
    )

    if variant == "original-unhandled":
        assert not any(
            row["event"] in ("close_sent", "transfer_sent", "probe_completed_nonterminal")
            for row in events
        )
        rejection = "has to answer queries" in log or "Got false in applying" in log
        return {
            "engineering_pass": False,
            "negative_control_unhandled_callback_observed": True,
            "native_rejection_observed": rejection,
            "winner": None,
            "game_completed": False,
            "note": (
                "A callback without reply is source-consistent negative evidence; "
                "no successful exchange is claimed."
            ),
        }

    assert {row["request_id"] for row in issued} == {row["request_id"] for row in applied}
    assert all(row["result"] == 1 for row in applied)
    replies = re.findall(r"DirectorAI: step finished result=(\d+)", log)
    assert len(replies) == len(issued) and all(int(result) != 0 for result in replies)
    assert not any(row.get("failed") for row in events)
    assert not any(
        row["event"]
        in (
            "fixture_hero_count_invalid",
            "fixture_target_invalid",
            "fixture_no_real_path",
            "transfer_fixture_invalid",
            "transfer_no_legal_slot",
        )
        for row in events
    )

    close_i, close = one(events, "close_sent")
    ack_i, ack = one(events, "close_ack")
    assert callback_i < close_i < ack_i
    assert close["request_id"] == ack["request_id"]
    assert close["query_id"] == callback["query_id"] == ack["query_id"]
    assert ack["result"] == 1, "Native QueryReply PackageApplied must succeed"
    assert ack["pending_move"] == 0
    assert ack["pending_queries"] == 0 and ack["query_requests"] == 0, (
        "Successful close must leave no pending query or request"
    )
    assert close["pending_queries"] == 1

    end_sent_i, end_sent = one(events, "endturn_sent")
    end_i, end = one(events, "endturn_ack")
    assert max(ack_i, close_i) < end_sent_i < end_i
    assert end["result"] == 1 and end["request_id"] == end_sent["request_id"]
    assert end["pending_move"] == 0
    assert end["pending_queries"] == 0 and end["query_requests"] == 0

    post = events[end_i + 1 :]
    allowed_post = {"unexpected_additional_turn"}
    assert all(row["event"] in allowed_post for row in post), (
        "Only a post-boundary turn notification may follow; no action is allowed"
    )
    assert not any(
        row["event"] in ("move_sent", "transfer_sent", "close_sent", "endturn_sent")
        for row in post
    )

    if variant == "transfer-close":
        sent_i, sent = one(events, "transfer_sent")
        tack_i, tack = one(events, "transfer_ack")
        assert callback_i < sent_i < tack_i < close_i
        assert sent["request_id"] == tack["request_id"]
        assert sent["query_id"] == callback["query_id"] == tack["query_id"]
        assert tack["result"] == 1
        assert tack["pending_queries"] == 1
    else:
        assert not any(row["event"] == "transfer_sent" for row in events)
        assert not any(row["event"] == "transfer_ack" for row in events)

    assert not any(
        token in log
        for token in (
            "has to answer queries",
            "Got false in applying",
            "external policy failed",
        )
    )
    assert not any(
        row["event"] in ("move_failed", "economy_failed", "query_failed") for row in trace
    )

    after = next(row for row in trace if row["event"] == "probe_after_close")
    donor = callback["courier"]
    receiver = callback["receiver"]
    db, rb = army(before, donor), army(before, receiver)
    da, ra = army(after, donor), army(after, receiver)
    assert sum(da.values()) >= 1 and sum(ra.values()) >= 1
    assert db + rb == da + ra, "Aggregate creature counts must be conserved"
    assert [
        (h["id"], h["x"], h["y"], h["z"]) for h in before["heroes"]
    ] == [
        (h["id"], h["x"], h["y"], h["z"]) for h in after["heroes"]
    ]
    assert (before["gold"], before["wood"], before["ore"]) == (
        after["gold"],
        after["wood"],
        after["ore"],
    )

    if variant == "transfer-close":
        assert db != da and rb != ra
        assert db - da == ra - rb
        assert bool(db - da)
    else:
        assert db == da and rb == ra

    return {
        "engineering_pass": True,
        "winner": None,
        "game_completed": False,
        "controlled_boundary": (
            "successful native EndTurn ACK after QueryReply close"
        ),
        "transfer_confirmed": variant == "transfer-close",
        "audit_gate": "v2-source-derived-close-ack-no-queryresolved",
        "queryresolved_event_expected": False,
        "queryresolved_source_reason": (
            "CGarrisonDialogQuery has no onRemoval/sendQueryResolved; "
            "successful QueryReply PackageApplied plus EndTurn ACK is the closure proof"
        ),
        "postcompletion_notifications": post,
        "training_samples": 0,
        "optimizer_steps": 0,
    }


def audit(directory):
    plan = json.loads((directory / "plan.json").read_text())
    execution = json.loads((directory / "execution.json").read_text())
    assert plan["engineering_only"] and not plan["policy_broker"]
    assert all(
        hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
        for path, digest in plan["hashes"].items()
    ), "Frozen input changed"
    assert execution["loaded_library_verified"] and not execution["loaded_library_errors"], (
        "Actual client/server capsule loading not proven"
    )
    assert plan["native_server_mode"] == "thread"
    assert plan["settings_server_useProcess"] is False

    events = load_lines(directory / "probe.jsonl")
    trace = load_lines(directory / "strategy-trace.jsonl")
    log = (directory / "client.log").read_text(errors="replace")
    thread_proof = thread_server_gate(
        execution["loaded_library_observations"],
        log,
        plan["settings_server_useProcess"],
    )
    assert thread_proof == execution["thread_server_verification"], (
        "Recorded thread-server evidence differs from independent gate"
    )

    result = gate(events, trace, log, plan["variant"])
    if result["engineering_pass"]:
        assert execution["controlled_stop"] and not execution["timed_out"]
        assert execution.get("stop_reason") == "proved_EndTurn_ACK_after_close"

    assert not list(directory.rglob("request-*.json"))
    assert not list(directory.rglob("action-*.json"))
    result.update(
        execution=execution,
        raw_sha256={
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                directory / "probe.jsonl",
                directory / "strategy-trace.jsonl",
                directory / "client.log",
            )
        },
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(args.run)
    except Exception as error:
        report = {
            "engineering_pass": False,
            "error": repr(error),
            "winner": None,
            "game_completed": False,
            "optimizer_steps": 0,
        }
    (args.run / "AUDIT_V2.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
