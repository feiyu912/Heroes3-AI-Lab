#!/usr/bin/env bash
# Headless full-adventure-game run (strategic-layer harness).
#
# Interface facts established by audit:
#   * vcmiclient supports --headless/--onlyAI/--testmap/--ai => AI-vs-AI full games need no GUI.
#   * The gym's ML server plugin is statically linked and throws
#       "Cannot track stats when randomHeroes is disabled"
#     for ANY non-battle game. Config.h reads server.ML.statsMode, but the shipped
#     config/schemas/settings.json declares server with additionalProperties:false and no ML key,
#     so the value is stripped before the plugin sees it.
#   * Fix without rebuilding the frozen battle binaries: give the worker its own private config
#     directory (copied from the build) with an extended schema that allows server.ML, and run with
#     CWD set there. The shared build config and all .so files stay untouched.
set -uo pipefail
LAB=/root/heroes3-ai-lab
BIN=$LAB/src/gym/vcmi/rel/bin
W=$LAB/workers/adv-run
MAPNAME="${1:-Maps/adv/adv-arena-01}"
AIONE="${2:-Nullkiller2}"
AITWO="${3:-Nullkiller2}"
SECS="${4:-240}"

rm -rf "$W"
mkdir -p "$W/data/vcmi/Maps/adv" "$W/data/vcmi/config"
ln -s "$LAB/data/vcmi/Data" "$W/data/vcmi/Data"
ln -s "$LAB/data/vcmi/Mods" "$W/data/vcmi/Mods"
cp "$LAB"/data/vcmi/Maps/adv/*.vmap "$W/data/vcmi/Maps/adv/" 2>/dev/null
cp -r "$BIN"/config "$W/config"

python3 - "$W" <<'PY'
import json, sys
from pathlib import Path
w = Path(sys.argv[1])

schema_path = w / 'config' / 'schemas' / 'settings.json'
raw = schema_path.read_text()
# VCMI ships this schema as JSON with leading // comments; strip whole-line comments before parsing.
stripped = '\n'.join(line for line in raw.splitlines() if not line.lstrip().startswith('//'))
schema = json.loads(stripped)
server = schema['properties']['server']
server.setdefault('properties', {})['ML'] = {
    'type': 'object',
    'additionalProperties': True,
    'default': {},
}
schema_path.write_text(json.dumps(schema, indent=2))

cfg = w / 'data' / 'vcmi' / 'config'
settings = {
    'mods': {'validation': 'off'},
    'general': {'music': 0, 'sound': 0, 'showIntro': False},
    'adventure': {'enemyMoveTime': 0, 'heroMoveTime': 0},
    'server': {'ML': {'statsMode': 'disabled'}},
    'session': {'onlyai': True},
}
# The client resolves "config/settings.json" relative to its working directory, and the server
# inherits that. Write it in both places so client and server see the same value.
for target in (cfg, w / 'config'):
    (target / 'settings.json').write_text(json.dumps(settings))
(cfg / 'modSettings.json').write_text(json.dumps({
    'activePreset': 'adv', 'presets': {'adv': {'mods': ['core', 'vcmi'], 'settings': {}}},
}))
for name in ['persistentStorage.json', 'keyBindingsConfig.json']:
    (cfg / name).write_text('{}')
PY

export LD_LIBRARY_PATH="$BIN:$LAB/onnxruntime/lib"
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export XDG_DATA_HOME="$W/data"
export XDG_CONFIG_HOME="$W"
export XDG_CACHE_HOME="$LAB/cache"

cd "$W" || exit 1
timeout "$SECS" "$BIN/vcmiclient" --headless --testmap "$MAPNAME" \
    --ai "$AIONE" --ai "$AITWO" --nointro --disable-video --savefrequency 1 \
    > "$W/client.log" 2>&1
echo "exit=$?"
echo "--- key lines ---"
grep -a -iE "Gamestate initialized|Failed to launch|Invalid map|victory|defeat|Game has ended|winner|Disaster|Reason:" "$W/client.log" | tail -15
echo "--- saves ---"
find "$W/data/vcmi/Saves" -type f 2>/dev/null | head
