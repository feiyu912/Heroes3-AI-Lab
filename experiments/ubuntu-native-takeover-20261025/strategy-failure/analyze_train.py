"""Read-only TRAIN logistics diagnosis; no torch, optimizer, engine or DEV rows."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
DELIVERY = PROJECT / "experiments/takeover-20261023/active-learning-delivery-01"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    manifest = read(DELIVERY / "ARCHIVE.json")
    assert manifest["passed"] and manifest["all_copied_SHA_equal"]
    inputs = {}

    def verified(path):
        path = Path(path)
        rel = str(path.relative_to(DELIVERY))
        expected = manifest["files"][rel]
        actual = sha(path)
        assert actual == expected["sha256"] and path.stat().st_size == expected["bytes"], rel
        inputs[rel] = actual
        return path

    def lines(path):
        return [json.loads(line) for line in verified(path).read_text().splitlines()]

    source_rel = "experiments/strategic-learned-recruitment-native-v3/candidate/AI/DirectorAI/CDirectorAI.cpp"
    frozen = verified(DELIVERY / "frozen-inputs/mnt/g/Heroes3-AI-Lab" / source_rel)
    source = PROJECT / source_rel
    assert sha(source) == sha(frozen)
    source_lines = source.read_text().splitlines()
    anchors = {}
    for label, literal in {
        "own_town_reinforcements": 'consider(obj->visitablePos(), 5, "own town reinforcements", 4)',
        "committed_move_filter": "else candidates.assign(1, committed);",
        "append_build_after_filter": "if(learnedBuildEnabled && buildWindow.open) appendBuildCandidates();",
        "append_recruit_after_filter": "if(learnedRecruitEnabled && buildWindow.open) appendRecruitCandidates();",
        "scripted_nohero_rescue": "cb->recruitHero(town, offers.front());",
    }.items():
        indices = [i + 1 for i, line in enumerate(source_lines) if literal in line]
        assert len(indices) == 1
        anchors[label] = dict(line=indices[0], literal=literal)

    results = []
    for arm in ("control", "curriculum"):
        for cell in range(8):
            root = DELIVERY / "native-study" / arm / f"cell-{cell:02d}"
            episode = read(verified(root / "admitted/episode.json"))
            rows = lines(root / "native/agent/typed-broker.jsonl")
            samples = lines(root / "admitted/samples.jsonl")
            traces = lines(root / "native/strategy-trace.jsonl")
            events = lines(root / "native/typed.jsonl")
            raw_audit = read(verified(root / "raw-audit/AUDIT.json"))
            assert raw_audit["passed"] and raw_audit["whole_game_valid"]
            assert raw_audit["full_state_recruitment_verified"] and raw_audit["free_transfer_verified"]
            assert episode["valid"] and episode["native"]["completed"] and episode["transport_drained"]
            assert len(rows) == len(samples) == episode["decisions"]
            job = episode["job"]
            assert job["arm"] == arm and job["seed"] == 2026104400 + cell
            assert job["opponent"] == ("Nullkiller2" if cell in (2, 3, 6, 7) else "EmptyAI")
            assert job["multiplier"] == (4 if arm == "curriculum" and job["opponent"] == "Nullkiller2" else 1)
            initial_hero = traces[0]["heroes"][0]["id"]
            counts = collections.Counter()
            early = collections.Counter()
            first_rows = []
            first_three_armies = []
            committed = {}
            commit_examples = []
            for row, sample in zip(rows, samples):
                q = row["request"]
                assert q == sample["request"] and row["action"] == sample["action"]
                assert row["request_sha256"] == sample["request_sha256"]
                assert row["old_value"] == sample["old_value"] and row["old_logprob"] == sample["old_logprob"]
                assert sample["valid"] and sample["execution_verified"] and sample["return"] == episode["reward"]
                candidates = q["candidates"]
                chosen = candidates[row["action"]]
                assert chosen["op"] == sample["action_type"] == row["response"]["op"]
                moves = [c for c in candidates if c["op"] == "move"]
                refills = [c for c in moves if c["kind"] == 4]
                stocked = [t for t in q["own_towns"] if t["army_value"] > 0]
                key = (q["hero"], q["own_turn"])
                previous = committed.get(key)
                retained_pattern = bool(previous and len(moves) == 1 and
                    (tuple(moves[0]["position"]), moves[0]["kind"]) == previous)
                compact = dict(decision_id=q["request_id"], day=q["day"], hero=q["hero"],
                    position=q["from"], movement=q["movement"], own_army_value=q["own_army_value"],
                    town_armies=[dict(town_id=t["town_id"], army_value=t["army_value"], position=t["position"]) for t in q["own_towns"]],
                    move_candidates=len(moves), refill_candidates=len(refills), selected=chosen,
                    consistent_with_prior_commit=retained_pattern)
                counts["decisions"] += 1
                counts[chosen["op"]] += 1
                counts["refill_offered"] += bool(refills)
                counts["refill_selected"] += chosen["op"] == "move" and chosen["kind"] == 4
                if stocked:
                    counts["stocked_requests"] += 1
                    counts["stocked_refill_offered"] += bool(refills)
                    counts["stocked_refill_unoffered"] += not refills
                    counts["stocked_single_nonrefill_move"] += len(moves) == 1 and not refills
                    counts["stocked_single_nonrefill_prior_commit_pattern"] += retained_pattern and not refills
                    if retained_pattern and not refills and len(commit_examples) < 5:
                        commit_examples.append(compact)
                if q["day"] <= 3:
                    first_rows.append(compact)
                    first_three_armies.append(q["own_army_value"])
                    early["decisions"] += 1
                    early[chosen["op"]] += 1
                    early["stocked_requests"] += bool(stocked)
                    early["refill_offered"] += bool(refills)
                    early["refill_selected"] += chosen["op"] == "move" and chosen["kind"] == 4
                    if chosen["op"] == "recruit":
                        early["recruit_gold"] += chosen["cost"]["gold"]
                        early["creatures_recruited"] += chosen["amount"]
                if chosen["op"] == "move":
                    committed[key] = (tuple(chosen["position"]), chosen["kind"])

            starts = [x for x in traces if x["event"] == "turn_start"]
            transfers = [x for x in traces if x["event"] == "before_army_transfer"]
            hires = [x for x in traces if x["event"] == "before_hire_hero"]
            disappearances = []
            appearances = []
            town_removals = []
            prior_heroes = {h["id"] for h in traces[0]["heroes"]}
            prior_towns = {t["id"] for t in traces[0]["towns"]}
            for line_no, snapshot in enumerate(traces[1:], 2):
                heroes = {h["id"] for h in snapshot["heroes"]}
                towns = {t["id"] for t in snapshot["towns"]}
                common = dict(day=snapshot["day"], event=snapshot["event"], trace_line=line_no)
                if prior_heroes - heroes:
                    disappearances.append(dict(common, hero_ids=sorted(prior_heroes - heroes)))
                if heroes - prior_heroes:
                    appearances.append(dict(common, hero_ids=sorted(heroes - prior_heroes)))
                if prior_towns - towns:
                    town_removals.append(dict(common, town_ids=sorted(prior_towns - towns)))
                prior_heroes, prior_towns = heroes, towns
            acknowledgements = [e for e in events if e["event"] == "free_transfer_ack_state"]
            assert all(e["success"] and e["state_change_verified"] for e in acknowledgements)
            assert len(acknowledgements) == len(transfers) == raw_audit["actual_transfers_checked"]
            assert raw_audit["actual_recruits_checked"] == counts["recruit"]
            assert raw_audit["actual_decisions_checked"] >= len(rows)
            terminal_snapshots = [t for t in traces if t["event"] in ("victory", "defeat")]
            assert len(terminal_snapshots) == 1
            terminal = terminal_snapshots[0]
            assert (terminal["event"] == "victory") == (episode["reward"] > 0)
            result = dict(arm=arm, cell=cell, job=job, reward=episode["reward"], counts=dict(counts),
                first_three_days=dict(early), first_three_army_max=max(first_three_armies),
                initial_hero_id=initial_hero,
                initial_hero_first_disappearance=next((d for d in disappearances if initial_hero in d["hero_ids"]), None),
                hero_disappearances=disappearances, hero_appearances=appearances, town_removals=town_removals,
                first_transfer_day=transfers[0]["day"] if transfers else None,
                transfer_ack_count=len(acknowledgements), scripted_hire_days=[s["day"] for s in hires],
                nohero_turn_start_days=[s["day"] for s in starts if not s["heroes"]],
                terminal_snapshot=dict(day=terminal["day"], event=terminal["event"], gold=terminal["gold"],
                    owned_hero_ids=sorted(h["id"] for h in terminal["heroes"]), owned_town_ids=sorted(t["id"] for t in terminal["towns"])),
                stock_and_retained_move_examples=commit_examples, first_three_day_requests=first_rows)
            results.append(result)
    totals = {}
    for opponent in ("Nullkiller2", "EmptyAI"):
        selected = [r for r in results if r["job"]["opponent"] == opponent]
        total = collections.Counter()
        for r in selected:
            total.update(r["counts"])
        totals[opponent] = dict(games=len(selected), wins=sum(r["reward"] > 0 for r in selected),
            counts=dict(total), scripted_hero_hires=sum(len(r["scripted_hire_days"]) for r in selected),
            first_hero_disappearance_games=sum(r["initial_hero_first_disappearance"] is not None for r in selected))
    assert sum(r["counts"]["decisions"] for r in results) == 8793
    assert totals["Nullkiller2"]["wins"] == 0 and totals["EmptyAI"]["wins"] == 8
    assert all(sha(DELIVERY / rel) == digest for rel, digest in inputs.items())
    report = dict(passed=True, script_sha256=sha(__file__), archive_manifest_sha256=sha(DELIVERY / "ARCHIVE.json"),
        source_sha256=sha(source), source_anchors=anchors, input_files_SHA_checked=inputs,
        totals=totals, TRAIN_games=16, TRAIN_admitted_requests_bound=8793, rows=results,
        native_games=0, optimizer_steps=0, GPU_operations=0, torch_imported=False, DEV_observation_rows_used=0,
        expert_labels=0, frozen_inputs_modified=False,
        limitations=["This reconstructs TRAIN logistics from existing raw requests, snapshots and actual transfer ACK states; it does not rerun the full native auditor.",
            "A stocked town without a refill candidate does not prove that a legal path to that town existed at that request. Retained-move patterns are descriptive, not counterfactual reachability proofs.",
            "A hero disappearing from owned snapshots can mean death, retreat or another native ownership change; this report does not classify it beyond the native event and observed absence.",
            "Return is the original completed episode +/-1, gamma=1; no temporal-discount failure is inferred.",
            "Existing scripted no-hero tavern rescue is present and observed; it is not learned hero recruitment.",
            "Neither candidate coverage nor a single early action is shown to cause the final loss."])
    (args.out / "AUDIT.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(dict(passed=True, totals=totals, TRAIN_games=16, TRAIN_rows=8793, checked_files=len(inputs)), ensure_ascii=False))


if __name__ == "__main__":
    main()
