#!/usr/bin/env python3
"""Fresh isolated hero-exchange probe with the v2 source-derived closure gate.

The v1 runner waited for an `exchange_query_resolved` event that CGarrisonDialogQuery
never emits. This runner stops only after the real close ACK, no pending query, and a
later successful EndTurn ACK. It uses the frozen multihero-capsules-03 binaries and
does not rebuild, train, or overwrite any v1 artifact.
"""
import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = HERE.parent / "multihero-mechanism-probe-v1"
sys.path.insert(0, str(V1))
from capsule_support import (
    verify_attestation,
    idle_locks,
    session_evidence,
    thread_server_gate,
)
from audit_run_v2 import audit

LAB = Path("/root/heroes3-ai-lab")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boundary_ready(path, variant):
    if not path.exists():
        return False
    rows = []
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            return False
    ends = [row for row in rows if row.get("event") == "endturn_ack"]
    if not ends or ends[-1].get("result") != 1:
        return False
    closes = [row for row in rows if row.get("event") == "close_ack"]
    if not closes:
        return False
    close = closes[-1]
    if (
        close.get("result") != 1
        or close.get("pending_queries") != 0
        or close.get("query_requests") != 0
    ):
        return False
    if variant == "transfer-close":
        transfers = [row for row in rows if row.get("event") == "transfer_ack"]
        if not transfers or transfers[-1].get("result") != 1:
            return False
    if variant == "close-only" and any(
        row.get("event") == "transfer_sent" for row in rows
    ):
        return False
    return True


def run(args):
    args.out = args.out.resolve()
    args.capsule = args.capsule.resolve()
    attestation = verify_attestation(args.capsule, args.variant)
    args.bin_dir = args.capsule / "bin"
    args.source_tree = args.capsule / "source-snapshot"
    assert args.bin_dir != (LAB / "src/vcmi-adv-build/bin").resolve(), (
        "Current training binaries forbidden"
    )
    assert args.source_tree != (LAB / "src/vcmi-adv").resolve(), (
        "Current training source tree forbidden"
    )

    variant = V1 / "candidates-02" / args.variant
    for name in ("CDirectorAI.cpp", "CDirectorAI.h"):
        assert (
            args.source_tree / "AI/DirectorAI" / name
        ).resolve() != (LAB / "src/vcmi-adv/AI/DirectorAI" / name).resolve()
        assert sha(args.source_tree / "AI/DirectorAI" / name) == sha(
            variant / name
        ), "Installed future candidate differs"

    required = [
        args.bin_dir / name for name in ("vcmiclient", "vcmiserver", "libvcmi.so")
    ]
    assert all(path.is_file() for path in required)

    barrier = HERE.parent / "adv-server-battle-barrier-v1/installed-source-sha256.json"
    manifest = json.loads(barrier.read_text())
    assert all(
        sha(args.source_tree / path) == digest for path, digest in manifest.items()
    ), "Retain certified server barrier sources"
    assert not os.environ.get("LAB_ADV_AGENT_DIR"), "Policy broker forbidden"

    args.out.mkdir(parents=True, exist_ok=False)
    work = args.out
    for name in ("data/vcmi/Maps/adv", "data/vcmi/config", "cache"):
        (work / name).mkdir(parents=True, exist_ok=True)
    shutil.copytree(args.bin_dir / "config", work / "config")
    assert (work / "config/filesystem.json").is_file(), "Client config incomplete"
    for name in ("Data", "Mods"):
        (work / "data/vcmi" / name).symlink_to(LAB / "data/vcmi" / name)
    # VCMIDirs::developmentMode() requires config/, Mods/, and a client binary
    # in the current directory. The accepted v1 runs had this top-level Mods
    # link; without it VCMI does not add ./config to the initial resource paths.
    (work / "Mods").symlink_to(LAB / "data/vcmi/Mods")
    # VCMI resolves its startup config relative to the launched executable's
    # directory. The accepted v1 runs launched this work-directory symlink, not
    # the capsule bin path directly. Keep that layout; /proc/exe still resolves
    # to the attested capsule binary and is verified below.
    client = work / "vcmiclient"
    client.symlink_to(args.bin_dir / "vcmiclient")
    fixture = work / "data/vcmi/Maps/adv/multihero-native-mechanism-probe-v1.vmap"
    shutil.copy2(V1 / "fixture-01.vmap", fixture)

    settings = {
        "mods": {"validation": "off"},
        "general": {"music": 0, "sound": 0, "showIntro": False},
        "adventure": {"enemyMoveTime": 0, "heroMoveTime": 0},
        "server": {"seed": args.seed, "useProcess": False},
        "session": {"onlyai": True},
    }
    for folder in (work / "config", work / "data/vcmi/config"):
        (folder / "settings.json").write_text(json.dumps(settings))
        (folder / "modSettings.json").write_text(
            json.dumps(
                {
                    "activePreset": "adv",
                    "presets": {"adv": {"mods": ["core", "vcmi"], "settings": {}}},
                }
            )
        )
        for name in ("persistentStorage.json", "keyBindingsConfig.json"):
            (folder / name).write_text("{}")

    # Snapshot exactly what the client was launched with. VCMI rewrites the
    # live config files during startup, so those mutable copies must not be
    # treated as frozen scientific inputs.
    initial_config = work / "initial-config"
    initial_data_config = work / "initial-data-config"
    shutil.copytree(work / "config", initial_config)
    shutil.copytree(work / "data/vcmi/config", initial_data_config)

    command = [
        str(work / "vcmiclient"),
        "--headless",
        "--testmap",
        "Maps/adv/multihero-native-mechanism-probe-v1",
        "--nointro",
        "--disable-video",
        "--savefrequency",
        "1",
    ]
    inputs = required + [
        args.source_tree / "AI/DirectorAI" / name
        for name in ("CDirectorAI.cpp", "CDirectorAI.h")
    ]
    inputs += [args.source_tree / path for path in manifest]
    inputs += [
        fixture,
        client,
        Path(__file__),
        HERE / "audit_run_v2.py",
        HERE / "AUDIT_SOURCE_REVIEW.md",
        V1 / "capsule_support.py",
        args.capsule / "BUILD_ATTESTATION.json",
        args.capsule.parent / "EXECUTION.json",
        barrier,
    ]
    inputs += [args.capsule / path for path in attestation["artifacts"]]
    inputs += sorted(initial_config.rglob("*.json"))
    inputs += sorted(initial_data_config.rglob("*.json"))

    plan = {
        "engineering_only": True,
        "policy_broker": False,
        "variant": args.variant,
        "seed": args.seed,
        "command": command,
        "source_tree": str(args.source_tree),
        "bin_dir": str(args.bin_dir),
        "out": str(work),
        "build_attestation": str(args.capsule / "BUILD_ATTESTATION.json"),
        "build_kind": attestation["build_kind"],
        "native_server_mode": "thread",
        "settings_server_useProcess": False,
        "audit_gate": "v2-source-derived-close-ack-no-queryresolved",
        "legacy_v1_audit_not_used": True,
        "hashes": {str(path): sha(path) for path in inputs},
        "training_samples": 0,
        "optimizer_steps": 0,
        "game_completed": False,
        "winner": None,
        "execute_requested": args.execute,
    }
    (work / "plan.json").write_text(json.dumps(plan, indent=2))
    if not args.execute:
        return {"prepared_only": True, "game_started": False}

    env = dict(
        os.environ,
        LD_LIBRARY_PATH=str(args.bin_dir),
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        XDG_DATA_HOME=str(work / "data"),
        XDG_CONFIG_HOME=str(work),
        XDG_CACHE_HOME=str(work / "cache"),
        LAB_ADV_AI_0="DirectorAI",
        LAB_ADV_AI_1="EmptyAI",
        LAB_ADV_TRACE=str(work / "strategy-trace.jsonl"),
        LAB_HERO_PROBE_LOG=str(work / "probe.jsonl"),
    )
    env.pop("LAB_ADV_DECISIONS", None)
    execution = {
        "controlled_stop": False,
        "timed_out": False,
        "game_completed": False,
        "winner": None,
        "optimizer_steps": 0,
    }
    loaded = {}
    load_errors = []
    with idle_locks():
        start = time.monotonic()
        with (work / "client.log").open("w") as log:
            child = subprocess.Popen(
                command,
                cwd=work,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                while child.poll() is None:
                    for observation in session_evidence(child.pid, args.bin_dir):
                        if not observation["libraries"]:
                            continue
                        old = loaded.get(str(observation["pid"]), {})
                        proof = {
                            thread["tid"]: thread
                            for thread in old.get("run_server_threads", [])
                        }
                        proof.update(
                            {
                                thread["tid"]: thread
                                for thread in observation.get("run_server_threads", [])
                            }
                        )
                        observation["run_server_threads"] = list(proof.values())
                        loaded[str(observation["pid"])] = observation
                        if not observation["valid"]:
                            load_errors.append(observation)
                    if load_errors:
                        execution["stop_reason"] = "loaded_capsule_identity_failure"
                        break
                    native = (work / "client.log").read_text(errors="replace")
                    if (
                        args.variant != "original-unhandled"
                        and boundary_ready(work / "probe.jsonl", args.variant)
                    ):
                        execution["controlled_stop"] = True
                        execution["stop_reason"] = "proved_EndTurn_ACK_after_close"
                        break
                    if (
                        args.variant == "original-unhandled"
                        and (work / "probe.jsonl").exists()
                        and '"event":"exchange_callback"'
                        in (work / "probe.jsonl").read_text(errors="replace")
                        and (
                            "has to answer queries" in native
                            or "Got false in applying" in native
                        )
                    ):
                        execution["controlled_stop"] = True
                        execution["stop_reason"] = (
                            "negative_control_native_query_rejection"
                        )
                        break
                    if time.monotonic() - start > args.seconds:
                        execution["timed_out"] = True
                        execution["stop_reason"] = "engineering_timeout_no_winner"
                        break
                    time.sleep(0.01)
            finally:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                execution["engine_exit"] = child.returncode
                execution["wall_seconds"] = time.monotonic() - start

    execution["loaded_library_observations"] = list(loaded.values())
    execution["loaded_library_errors"] = load_errors
    execution["loaded_library_verified"] = (
        bool(loaded)
        and not load_errors
        and all(observation["valid"] for observation in loaded.values())
        and any(
            Path(observation["executable"]).name == "vcmiclient"
            for observation in loaded.values()
        )
    )
    try:
        execution["thread_server_verification"] = thread_server_gate(
            list(loaded.values()),
            (work / "client.log").read_text(errors="replace"),
            settings["server"]["useProcess"],
        )
    except AssertionError as error:
        execution["thread_server_verification"] = {
            "passed": False,
            "mode": "thread",
            "error": str(error),
        }
    (work / "execution.json").write_text(json.dumps(execution, indent=2))
    try:
        result = audit(work)
    except Exception as error:
        result = {
            "engineering_pass": False,
            "error": repr(error),
            "game_completed": False,
            "winner": None,
            "optimizer_steps": 0,
        }
    (work / "AUDIT_V2.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variant",
        choices=("original-unhandled", "close-only", "transfer-close"),
        required=True,
    )
    parser.add_argument("--capsule", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026102501)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args)
    except BaseException as error:
        result = {
            "engineering_pass": False,
            "error": repr(error),
            "winner": None,
            "game_completed": False,
        }
        if args.out.is_dir():
            (args.out / "BLOCKED_OR_FAILED.json").write_text(
                json.dumps(result, indent=2)
            )
    print(json.dumps(result, indent=2))
    raise SystemExit(
        0
        if result.get("prepared_only")
        or result.get("engineering_pass")
        or (
            result.get("negative_control_unhandled_callback_observed")
            and result.get("native_rejection_observed")
            and not result.get("execution", {}).get("timed_out")
        )
        else 1
    )
