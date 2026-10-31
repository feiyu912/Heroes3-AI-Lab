#!/usr/bin/env python3
"""Fresh isolated two-mobile-hero scheduler probe.

The candidate keeps the original Director pickHero/findTarget scheduler and the
existing native request/ACK probe hooks, but removes the v1 single-turn meeting
stop. This runner uses the new scheduler capsule, never the current training
binaries, and never trains.
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
from capsule_support import (
    verify_attestation,
    idle_locks,
    session_evidence,
    thread_server_gate,
)
from audit_scheduler import audit

LAB = Path("/root/heroes3-ai-lab")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scheduler_ready(path):
    trace=path.parent/'strategy-trace.jsonl'
    if not path.exists() or not trace.exists(): return False
    try:
        rows=[json.loads(x) for x in path.read_text().splitlines() if x.strip()]
        states=[json.loads(x) for x in trace.read_text().splitlines() if x.strip()]
    except json.JSONDecodeError: return False
    if not any(r.get('event')=='garrison_setup_ack' and r.get('result')==1 for r in rows): return False
    for turn in (1,2):
        for hero in (0,2):
            sent={r['request_id'] for r in rows if r.get('event')=='move_sent' and r.get('hero')==hero and r.get('own_turn')==turn}
            ack={r['request_id'] for r in rows if r.get('event')=='move_ack' and r.get('result')==1 and r.get('hero')==hero and r.get('own_turn')==turn}
            positions={(h['x'],h['y'],h['z']) for r in states if r.get('own_turn')==turn for h in r.get('heroes',[]) if h['id']==hero}
            if not sent.intersection(ack) or len(positions)<2: return False
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

    variant = HERE / "candidates" / args.variant
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
    fixture = work / "data/vcmi/Maps/adv/multihero-scheduler-garrison-v3.vmap"
    shutil.copy2(HERE / "fixture-03.vmap", fixture)

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
        "Maps/adv/multihero-scheduler-garrison-v3",
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
        HERE / "audit_scheduler.py",
        HERE / "derive.py",
        HERE / "build_scheduler.py",
        HERE / "capsule_support.py",
        HERE / "fixture-02.json",
        args.capsule / "BUILD_ATTESTATION.json",
        args.capsule.parent / "EXECUTION.json",
        barrier,
    ]
    inputs += [args.capsule / path for path in attestation["artifacts"]]
    inputs += [HERE / "prepare.py", HERE / "FIXTURE_DERIVATION.json", HERE / "PLAN.md", HERE / "prepare_runner.py", HERE / "audit_legacy.py", HERE / "DERIVATION.json"]
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
        "audit_gate": "real-garrison-and-two-mobile-heroes-each-of-two-turns",
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
    env.pop("LAB_ADV_AGENT_DIR", None)
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
                    if scheduler_ready(work / "probe.jsonl"):
                        execution["controlled_stop"] = True
                        execution["stop_reason"] = (
                            "observed_two_mobile_heroes_two_turns"
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
    (work / "AUDIT_SCHEDULER.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variant",
        choices=("baseline", "filtered"),
        required=True,
    )
    parser.add_argument("--capsule", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2026102501)
    parser.add_argument("--seconds", type=int, default=45)
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
        0 if result.get("prepared_only") or result.get("engineering_pass") else 1
    )
