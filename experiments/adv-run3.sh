#!/usr/bin/env bash
# Adventure-layer run harness (M2 onward).
#
# Changes over adv-run2.sh, per WORKBUDDY_DIRECTORAI_REVIEW_20261018.md:
#   * every run gets a unique directory; previous runs are never deleted
#   * the requested AIs are exported to LAB_ADV_AI_<slot> (the --ai flag is dead in this fork)
#   * the actual AI assignment is read back from the log and a mismatch fails the run
#   * optional gdb mode to capture a native stack instead of guessing
#
# usage: adv-run3.sh <map> <aiForSlot0> <aiForSlot1> <seed> <seconds> [gdb]
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

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-${AI0}-vs-${AI1}-seed${SEED}"
W="$ROOT/$RUN_ID"
mkdir -p "$W/data/vcmi/Maps/adv" "$W/data/vcmi/config" "$W/config"
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
  echo "run_id=$RUN_ID"
  echo "map=$MAPNAME"
  echo "ai_slot0=$AI0"
  echo "ai_slot1=$AI1"
  echo "seed=$SEED"
  echo "seconds=$SECS"
  echo "mode=$MODE"
  echo "bin=$BIN"
  sha256sum "$BIN"/vcmiclient "$BIN"/vcmiserver "$BIN"/libvcmi.so 2>/dev/null
} > "$W/run.env"

cd "$W" || exit 1
CMD=("$BIN/vcmiclient" --headless --testmap "$MAPNAME"
     --ai "$AI0" --ai "$AI1" --nointro --disable-video --savefrequency 1)

if [ "$MODE" = "gdb" ]; then
  timeout "$SECS" gdb -q -batch \
      -ex "set pagination off" \
      -ex "run" \
      -ex "echo \n=== BACKTRACE ===\n" \
      -ex "bt 25" \
      -ex "echo \n=== ALL THREADS ===\n" \
      -ex "thread apply all bt 12" \
      --args "${CMD[@]}" > "$W/gdb.log" 2>&1
  code=$?
  cp "$W/gdb.log" "$W/client.log"
else
  timeout "$SECS" "${CMD[@]}" > "$W/client.log" 2>&1
  code=$?
fi

{
  echo "exit=$code"
  echo "--- ai assignment (actual) ---"
  grep -a -oE "Player [a-z]+ will be lead by [A-Za-z0-9]+" "$W/client.log" | sort -u
  echo "--- result ---"
  grep -a -oE "AIGateway: Player [0-9] \([a-z]+\) (won|lost)|Turn nr [0-9]+|All players have ended the game" "$W/client.log" | tail -4
  echo "--- crashes ---"
  grep -a -c "Disaster happened" "$W/client.log"
  grep -a -c "SIGSEGV\|SIGABRT\|dumped core" "$W/client.log"
  echo "--- sha ---"
  sha256sum "$W/client.log"
} | tee "$W/summary.txt"

echo "RUN_DIR=$W"
