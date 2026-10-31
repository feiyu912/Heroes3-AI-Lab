#!/usr/bin/env python3
"""Preserve the raw scheduler probe output and record hashes.

The source output remains in evaluations/. This copy is evidence only; it does
not mutate the source run, capsule, fixture, or shared source tree.
"""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path("/root/heroes3-ai-lab/evaluations/multihero-scheduler-probe-v1-01")
DEST = HERE / "native-evidence-01"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if DEST.exists():
    raise SystemExit(f"refusing to overwrite existing archive: {DEST}")
if not SOURCE.is_dir():
    raise SystemExit(f"source output missing: {SOURCE}")

shutil.copytree(SOURCE, DEST, symlinks=True)
files = {}
for path in sorted(DEST.rglob("*")):
    if path.is_file() and not path.is_symlink():
        files[str(path.relative_to(DEST))] = sha(path)
key_names = (
    "probe.jsonl",
    "strategy-trace.jsonl",
    "client.log",
    "plan.json",
    "execution.json",
    "AUDIT_SCHEDULER.json",
)
result = {
    "source": str(SOURCE),
    "destination": str(DEST),
    "source_preserved": True,
    "archive_is_copy": True,
    "raw_sha256": {
        name: files[name] for name in key_names if name in files
    },
    "all_file_sha256": files,
    "fixture_sha256": sha(HERE / "fixture-01.vmap"),
    "candidate_cpp_sha256": sha(HERE / "candidates/scheduler/CDirectorAI.cpp"),
    "candidate_h_sha256": sha(HERE / "candidates/scheduler/CDirectorAI.h"),
    "scheduler_lib_sha256": sha(
        Path(
            "/root/heroes3-ai-lab/evaluations/"
            "multihero-scheduler-capsule-01/scheduler/bin/libvcmi.so"
        )
    ),
    "build_attestation_sha256": sha(
        Path(
            "/root/heroes3-ai-lab/evaluations/"
            "multihero-scheduler-capsule-01/scheduler/BUILD_ATTESTATION.json"
        )
    ),
}
(DEST / "ARCHIVE.json").write_text(json.dumps(result, indent=2))
(HERE / "ENGINEERING_STOP.json").write_text(
    json.dumps(
        {
            "status": "scheduler_probe_not_qualified",
            "reason": "intended town-tile control hero 3 was mobile and was scheduled",
            "engineering_pass": False,
            "raw_evidence": str(DEST),
            "source_evidence": str(SOURCE),
            "raw_sha256": result["raw_sha256"],
            "observations": {
                "turn_open_count": 2,
                "mobile_heroes_with_successful_acks": [0, 2],
                "mobile_moves_observed_in_turns": [1, 2],
                "control_hero_3_scheduled": True,
                "failed_move_acks": 0,
            },
            "next_step": (
                "do not rerun silently; design a new fixture with a genuinely "
                "blocked or garrisoned control, or source-review and change the "
                "scheduler candidate to skip isGarrisoned heroes, as a new "
                "single-factor experiment"
            ),
        },
        indent=2,
    )
)
print(json.dumps(result, indent=2))
