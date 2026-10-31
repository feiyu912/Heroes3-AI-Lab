#!/usr/bin/env python3
"""Create a read-only manifest for the v2 native-evidence archive."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "native-evidence-v2"
RUNS = {
    "multihero-probe-close-v2-01": "startup_failure_missing_top_level_Mods",
    "multihero-probe-close-v2-02": "startup_failure_missing_top_level_Mods",
    "multihero-probe-close-v2-03": "native_close_ok_audit_frozen_input_failure",
    "multihero-probe-close-v2-04": "native_close_pass_v2_audit",
    "multihero-probe-transfer-v2-01": "native_transfer_close_pass_v2_audit",
}


def digest_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_manifest(run):
    entries = {}
    for folder, dirs, names in __import__("os").walk(run, followlinks=False):
        folder = Path(folder)
        for name in sorted(dirs + names):
            path = folder / name
            relative = str(path.relative_to(run))
            if path.is_symlink():
                entries[relative] = {
                    "symlink": __import__("os").readlink(path),
                    "lexists": path.exists(),
                }
                if name in dirs:
                    dirs.remove(name)
            elif path.is_file():
                entries[relative] = {
                    "sha256": digest_file(path),
                    "bytes": path.stat().st_size,
                }
    encoded = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return {
        "records": len(entries),
        "manifest_sha256": hashlib.sha256(encoded).hexdigest(),
        "entries": entries,
    }


def audit_summary(run):
    path = run / "AUDIT_V2.json"
    if not path.exists():
        return None
    report = json.loads(path.read_text())
    return {
        "engineering_pass": report.get("engineering_pass"),
        "error": report.get("error"),
        "transfer_confirmed": report.get("transfer_confirmed"),
        "audit_gate": report.get("audit_gate"),
        "postcompletion_notifications": len(
            report.get("postcompletion_notifications", [])
        ),
    }


def main():
    manifest = {
        "source_root": "/root/heroes3-ai-lab/evaluations",
        "archive_root": str(ARCHIVE),
        "read_only_raw_manifest": True,
        "capsules": {
            "close-only": {
                "path": "/root/heroes3-ai-lab/evaluations/multihero-capsules-03/close-only",
                "libvcmi_sha256": "27bffe10f81598e349a7ad54e04e30250dd2731bd06df8c15aa7f334e7bae625",
            },
            "transfer-close": {
                "path": "/root/heroes3-ai-lab/evaluations/multihero-capsules-03/transfer-close",
                "libvcmi_sha256": "1b6872474bfbb5fe4a8f544625e2cb3fe23b6e443395433e49392b7df7021004",
            },
        },
        "runs": {},
    }
    for name, status in RUNS.items():
        run = ARCHIVE / name
        assert run.is_dir(), name
        record = run_manifest(run)
        record["status"] = status
        record["audit_v2"] = audit_summary(run)
        manifest["runs"][name] = record
    (ARCHIVE / "ARCHIVE.json").write_text(json.dumps(manifest, indent=2))
    print(
        json.dumps(
            {
                name: {
                    "status": record["status"],
                    "records": record["records"],
                    "manifest_sha256": record["manifest_sha256"],
                    "audit_v2": record["audit_v2"],
                }
                for name, record in manifest["runs"].items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
