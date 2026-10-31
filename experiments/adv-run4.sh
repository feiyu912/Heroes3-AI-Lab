#!/usr/bin/env bash
# Adventure-layer run harness (M2, hardened per WORKBUDDY_DIRECTORAI_PATH_REVIEW_20261018.md).
#
#   * every run gets a unique directory created with mktemp; an existing directory is a hard error
#   * the requested AIs are exported to LAB_ADV_AI_<slot> (the --ai flag is dead in this fork)
#   * the actual AI assignment is read back from the log and a MISMATCH fails the run
#   * the game's own exit status is propagated, not gdb's and not the trailing echo
#
# usage: adv-run4.sh <map> <aiForSlot0> <aiForSlot1> <seed> <seconds> [mode]
#        mode: run (default) | gdb
set -uo pipefail
LAB=/root/heroes3-ai-lab
BIN=$LAB/src/vcmi-adv-build/bin
ROOT=$LAB/workers/adv-runs

MAPNAME="${1:-Maps/adv/adv-arena-01}"
AI0="${2:-Nullkiller2}"
AI1="${3:-Nullkiller2}"
SEED="${4:-2026101801}"
SECS="${5:-240}"
MODE="${6:-run}"

# Unique run directory: refuse to reuse, never delete a previous run.
STAMP="$(date -u +%Y%m%dT%H%M%S)"
W="$ROOT/${STAMP}-${AI0}-vs-${AI1}-seed${SEED}-$(mktemp -u XXXXXXXX)"
if [ -e "$W" ]; then
    echo "FATAL: run directory already exists, refusing to overwrite: $W" >&2
    exit 3
fi
mkdir -p "$W/data/vcmi/Maps/adv" "$W/data/vcmi/config" "$W/config" || exit 3
ln -sfn "$LAB/data/vcmi/Data" "$W/data/vcmi/Data"
ln -sfn "$LAB/data/vcmi/Mods" "$W/data/vcmi/Mods"
cp "$LAB"/data/vcmi/Maps/adv/*.vmap "$W/data/vcmi/Maps/adv/" 2>/dev/null
cp -r "$BIN"/config/. "$W/config/" 2>/dev/null

python3 - "$W" "$SEED" <<'PY'
import json, sys
from pathlib import Path
w = Path(sys.argv[1]); seed = int(sys.argv[2])
settings = {
    'mods': {'validation': 'off'},
    'general': {'music': 0, 'sound': 0, 'showIntro': False},
    'adventure': {'enemyMoveTime': 0, 'heroMoveTime': 0},
    'server': {'seed': seed},
    'session': {'onlyai': True},
}
for target in (w / 'data' / 'vcmi' / 'config', w / 'config'):
    target.mkdir(parents=True, exist_ok=True)
    (target / 'settings.json').write_text(json.dumps(settings))
    (target / 'modSettings.json').write_text(json.dumps({
        'activePreset': 'adv', 'presets': {'adv': {'mods': ['core', 'vcmi'], 'settings': {}}},
    }))
    for name in ['persistentStorage.json', 'keyBindingsConfig.json']:
        (target / name).write_text('{}')
PY

export LD_LIBRARY_PATH="$BIN"
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export XDG_DATA_HOME="$W/data" XDG_CONFIG_HOME="$W" XDG_CACHE_HOME="$W/cache"
export LAB_ADV_AI_0="$AI0" LAB_ADV_AI_1="$AI1"

{
  echo "run_dir=$W"
  echo "mode=$MODE"
  echo "map=$MAPNAME"
  echo "ai_slot0=$AI0"
  echo "ai_slot1=$AI1"
  echo "seed=$SEED"
  echo "seconds=$SECS"
  echo "bin=$BIN"
  sha256sum "$BIN"/vcmiclient "$BIN"/vcmiserver "$BIN"/libvcmi.so 2>/dev/null
} | tee "$W/run.env"

cd "$W" || exit 3
CMD=("$BIN/vcmiclient" --headless --testmap "$MAPNAME"
     --ai "$AI0" --ai "$AI1" --nointro --disable-video --savefrequency 1)

if [ "$MODE" = "gdb" ]; then
  timeout "$SECS" gdb -q -batch \
      -ex "set pagination off" \
      -ex "run" \
      -ex "echo \n=== BACKTRACE ===\n" \
      -ex "bt 25" \
      --args "${CMD[@]}" > "$W/client.log" 2>&1
  code=$?
else
  timeout "$SECS" "${CMD[@]}" > "$W/client.log" 2>&1
  code=$?
fi

# Result record: engine exit, AI assignment, native game result, crash/timeout.
python3 - "$W" "$AI0" "$AI1" "$MAPNAME" "$SEED" "$code" "$MODE" > "$W/result.json" <<'PY'
import json, re, sys
from pathlib import Path

w, ai0, ai1, mapname, seed, code, mode = sys.argv[1:8]
log = Path(w, 'client.log').read_text(errors='replace')

assignment = dict(re.findall(r"Player ([a-z]+) will be lead by ([A-Za-z0-9]+)", log))
expected = {'red': ai0, 'blue': ai1}
match = assignment == expected

winner = re.findall(r"AIGateway: Player (\d) \((\w+)\) won", log)
turn = re.findall(r"Turn nr (\d+)", log)
crashes = log.count("Disaster happened")
aborts = len(re.findall(r"SIGSEGV|SIGABRT|dumped core", log))

result = {
    "run_dir": w,
    "mode": mode,
    "map": mapname,
    "seed": int(seed),
    "requested_ai": {"slot0": ai0, "slot1": ai1},
    "actual_ai": assignment,
    "ai_assignment_ok": match,
    "engine_exit": int(code),
    "timed_out": int(code) == 124,
    "crashed": crashes > 0 or aborts > 0,
    "winner": winner[-1] if winner else None,
    "turns": int(turn[-1]) if turn else None,
    "log_bytes": len(log),
}
print(json.dumps(result, indent=2))

if not match:
    print("FATAL: AI assignment mismatch, requested %s got %s" % (expected, assignment), file=sys.stderr)
    sys.exit(4)
if result["crashed"]:
    print("FATAL: crash detected in this run", file=sys.stderr)
    sys.exit(5)
PY
rc=$?

echo "--- verdict ---"
python3 - "$W" "$rc" <<'PY'
import json, sys
from pathlib import Path
r = json.loads(Path(sys.argv[1], 'result.json').read_text())
harness_rc = int(sys.argv[2])
v = {}
v["completed"] = r["turns"] is not None and r["winner"] is not None and not r["timed_out"]
v["ai_assignment_ok"] = r["ai_assignment_ok"]
v["crashed"] = r["crashed"]
v["engine_exit"] = r["engine_exit"]
for k, val in v.items():
    print("%-20s %s" % (k, val))
print("VERDICT: %s" % ("COMPLETE" if v["completed"] else "INCOMPLETE"))
sys.exit(harness_rc)
PY
exit $?
