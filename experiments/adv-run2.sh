#!/usr/bin/env bash
# Full adventure game on the isolated ENABLE_ML=OFF build.
#   BIN  : /root/heroes3-ai-lab/src/vcmi-adv-build/bin  (no libmlserverplugin dependency)
#   data : lab game assets via symlink, private Maps/config/Saves
#   map  : Maps/adv/adv-arena-01  (core heroes; see make-adv-map.py)
set -uo pipefail
LAB=/root/heroes3-ai-lab
BIN=$LAB/src/vcmi-adv-build/bin
W=$LAB/workers/adv-run2
MAPNAME="${1:-Maps/adv/adv-arena-01}"
AIONE="${2:-Nullkiller2}"
AITWO="${3:-Nullkiller2}"
SECS="${4:-300}"
SEED="${5:-2026101801}"

rm -rf "$W"
mkdir -p "$W/data/vcmi/Maps/adv" "$W/data/vcmi/config" "$W/config"
ln -s "$LAB/data/vcmi/Data" "$W/data/vcmi/Data"
ln -s "$LAB/data/vcmi/Mods" "$W/data/vcmi/Mods"
cp "$LAB"/data/vcmi/Maps/adv/*.vmap "$W/data/vcmi/Maps/adv/" 2>/dev/null
cp -r "$BIN"/config/. "$W/config/" 2>/dev/null

python3 - "$W" "$SEED" <<'PY'
import json, sys
from pathlib import Path
w = Path(sys.argv[1])
seed = int(sys.argv[2])
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
export XDG_DATA_HOME="$W/data"
export XDG_CONFIG_HOME="$W"
export XDG_CACHE_HOME="$W/cache"

cd "$W" || exit 1
timeout "$SECS" "$BIN/vcmiclient" --headless --testmap "$MAPNAME" \
    --ai "$AIONE" --ai "$AITWO" --nointro --disable-video --savefrequency 1 \
    --spectate --spectate-ignore-hero \
    > "$W/client.log" 2>&1
code=$?
echo "exit=$code"
echo "--- key lines ---"
grep -a -iE "Gamestate initialized|Failed to launch|Invalid map|victory|defeat|Game has ended|winner|Disaster|Reason:|new day|day [0-9]" "$W/client.log" | tail -25
echo "--- saves ---"
find "$W/data/vcmi/Saves" "$W/Saves" -type f 2>/dev/null | head
