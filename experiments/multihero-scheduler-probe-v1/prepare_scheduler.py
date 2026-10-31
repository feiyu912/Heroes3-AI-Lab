#!/usr/bin/env python3
"""Prepare the isolated scheduler probe candidate and fixture.

This reads the accepted Director source without modifying it. It derives a new
candidate from the preserved v1 probe source, restores the original pickHero /
findTarget scheduler, keeps the existing probe event hooks, and removes the
single-turn meeting stop. It also builds a new map artifact; it does not install
the map or launch VCMI.
"""
import copy
import hashlib
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
V1 = HERE.parent / "multihero-mechanism-probe-v1"
BASE = V1 / "candidates-02/original-unhandled"
ORIGINAL = Path("/root/heroes3-ai-lab/src/vcmi-adv/AI/DirectorAI")
OUT = HERE / "candidates" / "scheduler"
SOURCE_MAP = Path("/root/heroes3-ai-lab/data/vcmi/Maps/adv/takeover-v2-train-01-mines.vmap")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def block(text, start, end):
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def patch_source():
    base = (BASE / "CDirectorAI.cpp").read_text()
    header = (BASE / "CDirectorAI.h").read_text()
    original = (ORIGINAL / "CDirectorAI.cpp").read_text()

    base_pick = block(
        base,
        "const CGHeroInstance * CDirectorAI::pickHero",
        "bool CDirectorAI::findTarget",
    )
    base_find = block(
        base,
        "bool CDirectorAI::findTarget",
        "bool CDirectorAI::issueMove",
    )
    original_pick = block(
        original,
        "const CGHeroInstance * CDirectorAI::pickHero",
        "bool CDirectorAI::findTarget",
    )
    original_find = block(
        original,
        "bool CDirectorAI::findTarget",
        "bool CDirectorAI::issueMove",
    )

    source = base.replace(base_pick, original_pick, 1)
    assert source != base
    source = source.replace(base_find, original_find, 1)
    assert source != base

    # The accepted source's external-policy branch is never used in this probe.
    # Keep the symbol available but do not activate a policy broker.
    assert "chooseExternalCandidate" in source
    stub = """
int CDirectorAI::chooseExternalCandidate(const CGHeroInstance * hero) const
{
    (void)hero;
    return selectedCandidate;
}
"""
    source = source.replace(
        "bool CDirectorAI::issueMove()",
        stub + "\nbool CDirectorAI::issueMove()",
        1,
    )

    # Allow more than one own turn. The meeting probe intentionally stopped at
    # the first EndTurn ACK; the scheduler test must observe turn two.
    meeting_stop = (
        '    if(probeEndAck) { probeEvent("unexpected_additional_turn"); return; }\n'
    )
    assert source.count(meeting_stop) == 1
    source = source.replace(meeting_stop, "", 1)

    # Match the accepted scheduler's per-turn cap rather than the probe's
    # meeting-only cap.
    assert "if(movesThisTurn >= 8)" in source
    source = source.replace("if(movesThisTurn >= 8)", "if(movesThisTurn >= MAX_MOVES_PER_TURN)", 1)

    # Record which hero owned each move. move_sent/move_ack otherwise lack hero
    # identity in the v1 event schema.
    needle = '\ttraceState("before_move");\n\tprobeEvent("move_issued");'
    assert source.count(needle) == 1
    source = source.replace(
        needle,
        '\ttraceState("before_move");\n\tprobeHero = hero->id.getNum();\n\tprobeEvent("move_issued");',
        1,
    )

    old_event = (
        'out << "{\\"schema\\":\\"multihero-native-mechanism-probe-v1\\",'
        '\\"variant\\":\\"original-unhandled\\",\\"event\\":\\"" << event\n'
    )
    new_event = (
        'out << "{\\"schema\\":\\"multihero-scheduler-probe-v1\\",'
        '\\"variant\\":\\"scheduler\\",\\"event\\":\\"" << event\n'
    )
    assert old_event in source, "probeEvent schema line not found"
    source = source.replace(old_event, new_event, 1)
    assert source.count('<< ",\\"own_turn\\":" << ownTurns << "}\\n";') == 1
    source = source.replace(
        '<< ",\\"own_turn\\":" << ownTurns << "}\\n";',
        '<< ",\\"own_turn\\":" << ownTurns << ",\\"hero\\":" << probeHero << "}\\n";',
        1,
    )

    # Header: add the external-policy stub and the instrumented hero id.
    assert "bool issueMove();" in header
    header = header.replace(
        "bool issueMove();",
        "int chooseExternalCandidate(const CGHeroInstance * hero) const;\n\tbool issueMove();",
        1,
    )
    assert "ObjectInstanceID pendingHero;" in header
    header = header.replace(
        "ObjectInstanceID pendingHero;",
        "ObjectInstanceID pendingHero;\n\tint probeHero = -1;",
        1,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "CDirectorAI.cpp").write_text(source)
    (OUT / "CDirectorAI.h").write_text(header)
    return {
        "candidate_cpp_sha256": sha(OUT / "CDirectorAI.cpp"),
        "candidate_h_sha256": sha(OUT / "CDirectorAI.h"),
        "accepted_cpp_sha256": sha(ORIGINAL / "CDirectorAI.cpp"),
        "accepted_h_sha256": sha(ORIGINAL / "CDirectorAI.h"),
        "base_cpp_sha256": sha(BASE / "CDirectorAI.cpp"),
        "base_h_sha256": sha(BASE / "CDirectorAI.h"),
    }


def make_fixture():
    raw = SOURCE_MAP.read_bytes()
    with zipfile.ZipFile(SOURCE_MAP) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    header = json.loads(entries["header.json"])
    objects = json.loads(entries["objects.json"])
    assert header["mapLevels"]["surface"]["width"] == 36
    assert header["mapLevels"]["surface"]["height"] == 36

    donor = copy.deepcopy(objects["hero_0"])
    hero_a = copy.deepcopy(donor)
    hero_b = copy.deepcopy(donor)
    control = copy.deepcopy(donor)
    hero_a.update(x=8, y=10)
    hero_b.update(x=11, y=10)
    control.update(x=8, y=8)  # own town tile; expected garrison/control
    hero_a["options"].update(
        name="scheduler alpha",
        type="core:christian",
        owner="red",
        army=[
            {"type": "core:pikeman", "amount": 20},
            {"type": "core:archer", "amount": 10},
        ],
    )
    hero_b["options"].update(
        name="scheduler beta",
        type="core:tyris",
        owner="red",
        army=[
            {"type": "core:pikeman", "amount": 12},
            {"type": "core:archer", "amount": 6},
        ],
    )
    control["options"].update(
        name="scheduler blocked control",
        type="core:christian",
        owner="red",
        army=[{"type": "core:pikeman", "amount": 1}],
    )

    # Two separate current-turn visible pickups per mobile hero. Resources are
    # used instead of monsters so the probe observes movement, not battle.
    def resource(key, x, y, amount):
        value = copy.deepcopy(objects["resource_left_gold"])
        value.update(x=x, y=y)
        value["options"]["amount"] = amount
        return value

    selected = {
        "town_0": copy.deepcopy(objects["town_0"]),
        "town_1": copy.deepcopy(objects["town_1"]),
        "hero_1": copy.deepcopy(objects["hero_1"]),
        "hero_0": hero_a,
        "hero_2": hero_b,
        "hero_3": control,
        "resource_a1": resource("resource_a1", 9, 11, 500),
        "resource_a2": resource("resource_a2", 7, 11, 500),
        "resource_b1": resource("resource_b1", 12, 11, 500),
        "resource_b2": resource("resource_b2", 10, 11, 500),
    }
    header["name"] = "multihero-scheduler-probe-v1"
    header["description"] = (
        "ENGINEERING ONLY: two mobile owned heroes, separate visible pickups, "
        "one town-tile control, no training or ability score."
    )
    header["players"]["red"]["heroes"] = {
        "hero_0": {"type": "core:christian"},
        "hero_2": {"type": "core:tyris"},
        "hero_3": {"type": "core:christian"},
    }
    header["players"]["blue"]["heroes"] = {"hero_1": {"type": "core:sorsha"}}
    header["mods"] = None
    entries["header.json"] = json.dumps(header, sort_keys=True, indent=2).encode()
    entries["objects.json"] = json.dumps(selected, sort_keys=True, indent=2).encode()

    out = HERE / "fixture-01.vmap"
    assert not out.exists()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 23, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    manifest = {
        "source": str(SOURCE_MAP),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "map": str(out),
        "sha256": sha(out),
        "installed": False,
        "loaded_by_native": False,
        "red_heroes": 3,
        "mobile_heroes": [0, 2],
        "control_hero": 3,
        "enemy_control_hero": 1,
        "targets": {
            "hero_0": [["resource_a1", 9, 11], ["resource_a2", 7, 11]],
            "hero_2": [["resource_b1", 12, 11], ["resource_b2", 10, 11]],
        },
        "positions_are_object_coordinates": True,
        "native_pathfinding_still_required": True,
    }
    (HERE / "fixture-01.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    result = {"source_patch": patch_source(), "fixture": make_fixture()}
    print(json.dumps(result, indent=2))
