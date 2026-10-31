"""Validate a strategic schema6 BC dataset before any optimizer step.

Accepted record shapes
----------------------
1. One decision per line::

       {"request": {...schema6...}, "action": 17, "episode_id": "map-...", "split": "train"}

2. One trajectory per line::

       {"record_type": "episode", "episode_id": "...", "split": "train",
        "source": {...}, "decisions": [{"request": {...}, "action": 17}, ...]}

The validator never synthesizes a legal action, never changes a label, and never
uses a test split for training.  It writes ``DATASET_AUDIT.json`` and exits 1 on
any hard error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from bc_common import CATALOG_SHA256, configure_catalog, encoder, read_jsonl, sha256, write_json


def canonical_request(request: dict) -> str:
    value = dict(request)
    value.pop("request_id", None)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def normalize(path: Path, row: dict, catalog):
    if row.get("schema") == "expert-demonstration-v1" or "decisions" in row and "observation" in str(row)[:2000] and "request" not in str(row)[:2000]:
        raise ValueError("battle expert-demonstration-v1 belongs to the battle BC pipeline, not schema6 strategic BC")
    source = row.get("source") if isinstance(row.get("source"), dict) else {}
    if source.get("action_origin") == "video_guess":
        raise ValueError("video_guess actions are not trainable labels")
    if row.get("record_type") == "episode" or isinstance(row.get("decisions"), list):
        episode_id = row.get("episode_id") or row.get("episode") or path.stem
        if not isinstance(episode_id, str) or not episode_id:
            raise ValueError("episode requires a nonempty episode_id")
        split = row.get("split", "unspecified")
        output = []
        for index, decision in enumerate(row.get("decisions", [])):
            if not isinstance(decision, dict) or "request" not in decision:
                raise ValueError(f"{path}: episode {episode_id} decision {index} lacks request")
            item = dict(decision)
            item.setdefault("episode_id", episode_id)
            item.setdefault("split", split)
            item.setdefault("source", source)
            item.setdefault("decision_index", index)
            output.append(item)
        if not output:
            raise ValueError(f"{path}: episode {episode_id} has no decisions")
        return output
    if "request" not in row:
        raise ValueError(f"{path}: record lacks request")
    return [dict(row)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, nargs="+", required=True, help="JSONL files or directories")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--require-split", action="store_true", help="Reject records with split=unspecified")
    parser.add_argument("--quality-gate", choices=("none", "q2", "q3"), default="q2")
    parser.add_argument("--min-samples", type=int, default=1)
    parser.add_argument("--max-conflict-examples", type=int, default=20)
    args = parser.parse_args()

    catalog = configure_catalog()
    files = []
    for item in args.dataset:
        if item.is_dir():
            files.extend(sorted(item.rglob("*.jsonl")))
        else:
            files.append(item)
    files = sorted({path.resolve() for path in files})
    if not files:
        raise SystemExit("no JSONL files found")

    errors, warnings, conflict_examples = [], [], []
    records = []
    per_file = {}
    seen = {}
    duplicate_conflicts = 0
    for path in files:
        file_rows = read_jsonl(path)
        accepted = 0
        for number, row in enumerate(file_rows, 1):
            try:
                items = normalize(path, row, catalog)
            except ValueError as error:
                errors.append(f"{path}:{number}: {error}")
                continue
            for item in items:
                request = item.get("request")
                try:
                    encoder.validate(request, catalog=catalog)
                except (ValueError, TypeError) as error:
                    errors.append(f"{path}:{number}: invalid schema6 request: {error}")
                    continue
                action = item.get("action", item.get("selected_index"))
                if type(action) is not int or not 0 <= action < len(request["candidates"]):
                    errors.append(f"{path}:{number}: action must be an int candidate index in range")
                    continue
                action_type = item.get("action_type", request["candidates"][action]["op"])
                if action_type != request["candidates"][action]["op"]:
                    errors.append(f"{path}:{number}: action_type {action_type!r} differs from candidate op")
                    continue
                if request.get("creature_catalog_sha256") != CATALOG_SHA256:
                    errors.append(f"{path}:{number}: request catalog SHA differs from pinned catalog")
                    continue
                episode_id = item.get("episode_id")
                if not isinstance(episode_id, (str, int)) or isinstance(episode_id, bool) or str(episode_id) == "":
                    errors.append(f"{path}:{number}: episode_id required")
                    continue
                split = item.get("split", "unspecified")
                if split not in ("train", "validation", "val", "test", "unspecified"):
                    errors.append(f"{path}:{number}: unknown split {split!r}")
                    continue
                if args.require_split and split == "unspecified":
                    errors.append(f"{path}:{number}: explicit split required")
                    continue
                tier = item.get("quality_tier") or item.get("quality") or (item.get("source") or {}).get("quality_tier")
                if args.quality_gate == "q3" and tier != "Q3":
                    errors.append(f"{path}:{number}: Q3 quality gate requires quality_tier=Q3 (got {tier!r})")
                    continue
                if args.quality_gate == "q2" and tier == "Q0":
                    errors.append(f"{path}:{number}: Q0 records are not trainable")
                    continue
                return_value = item.get("return", item.get("value"))
                if return_value is not None and (isinstance(return_value, bool) or not isinstance(return_value, (int, float))):
                    errors.append(f"{path}:{number}: return/value must be numeric or absent")
                    continue
                key = canonical_request(request)
                if key in seen:
                    prior = seen[key]
                    if prior["action"] != action:
                        duplicate_conflicts += 1
                        if len(conflict_examples) < args.max_conflict_examples:
                            conflict_examples.append(dict(
                                request_sha256=key,
                                first=dict(file=prior["file"], line=prior["line"], action=prior["action"]),
                                second=dict(file=str(path), line=number, action=action),
                                candidate_ops=[c["op"] for c in request["candidates"]][:8],
                            ))
                        warnings.append(f"conflicting duplicate state {key[:12]} at {path}:{number} (kept first label)")
                        continue
                    warnings.append(f"duplicate state {key[:12]} at {path}:{number} (kept first)")
                    continue
                seen[key] = dict(file=str(path), line=number, action=action)
                records.append(dict(
                    request=request,
                    action=action,
                    action_type=action_type,
                    episode_id=str(episode_id),
                    split="validation" if split == "val" else split,
                    decision_index=item.get("decision_index"),
                    return_value=return_value,
                    quality_tier=tier,
                    source=item.get("source") or {},
                    file=str(path),
                    line=number,
                    request_sha256=key,
                ))
                accepted += 1
        per_file[str(path)] = dict(rows=len(file_rows), accepted=accepted, sha256=sha256(path))

    if len(records) < args.min_samples:
        errors.append(f"only {len(records)} unique decisions; min-samples={args.min_samples}")

    split_counts = Counter(record["split"] for record in records)
    action_counts = Counter(record["action_type"] for record in records)
    by_split_action = defaultdict(Counter)
    by_split_episode = defaultdict(set)
    for record in records:
        by_split_action[record["split"]][record["action_type"]] += 1
        by_split_episode[record["split"]].add(record["episode_id"])
    hashes = {split: {record["request_sha256"] for record in records if record["split"] == split} for split in split_counts}
    overlap = {}
    splits = sorted(hashes)
    for i, left in enumerate(splits):
        for right in splits[i + 1:]:
            overlap[f"{left}/{right}"] = len(hashes[left] & hashes[right])
            if overlap[f"{left}/{right}"]:
                errors.append(f"exact request leakage between {left} and {right}: {overlap[f'{left}/{right}']}")
    if split_counts.get("unspecified") and len(split_counts) > 1:
        warnings.append("mixed explicit and unspecified splits; the trainer will treat unspecified as train only if explicitly allowed")

    audit = dict(
        schema="strategic-bc-dataset-audit-v1",
        passed=not errors,
        catalog_sha256=CATALOG_SHA256,
        encoder_version=encoder.ENCODER_VERSION,
        files=per_file,
        unique_decisions=len(records),
        split_counts=dict(split_counts),
        split_episodes={key: sorted(value) for key, value in by_split_episode.items()},
        action_counts=dict(action_counts),
        action_counts_by_split={key: dict(value) for key, value in by_split_action.items()},
        exact_request_overlap=overlap,
        duplicate_state_kept_first=sum(1 for value in seen.values() if value),
        conflicting_duplicates_skipped=duplicate_conflicts,
        conflict_examples=conflict_examples,
        errors=errors,
        warnings=warnings[:200],
        quality_gate=args.quality_gate,
        limitations=[
            "A legal candidate index is not proof that the label is optimal or that a video showed this exact engine state.",
            "Video commentary must be converted to a rule teacher or an engine-executed reconstruction; a guessed action is not a human demonstration.",
            "Legality and fit do not prove game strength; paired native evaluation is required after training.",
        ],
    )
    write_json(args.out, audit)
    print(json.dumps({key: audit[key] for key in ("passed", "unique_decisions", "split_counts", "action_counts", "errors", "warnings")}, indent=2))
    return 0 if audit["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
