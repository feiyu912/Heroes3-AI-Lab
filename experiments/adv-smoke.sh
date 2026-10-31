#!/usr/bin/env bash
# Headless full-adventure-game smoke test with native VCMI AIs.
# Purpose: prove the client can load an adventure map, run AI turns, and reach a native result.
set -uo pipefail

LAB=/root/heroes3-ai-lab
BIN=$LAB/src/gym/vcmi/rel/bin
W=$LAB/workers/adv-smoke3
MAPNAME="${1:-diverse-192.vmap}"
AIONE="${2:-Nullkiller2}"
AITWO="${3:-Nullkiller2}"
SECS="${4:-180}"

rm -rf "$W"
mkdir -p "$W/data/vcmi/Maps" "$W/data/vcmi/config"
ln -s "$LAB/data/vcmi/Data" "$W/data/vcmi/Data"
ln -s "$LAB/data/vcmi/Mods" "$W/data/vcmi/Mods"
cp "$LAB"/data/vcmi/Maps/lab/*.vmap "$W/data/vcmi/Maps/" 2>/dev/null
cp "$LAB"/workers/adv-smoke/data/vcmi/config/*.json "$W/data/vcmi/config/" 2>/dev/null

export LD_LIBRARY_PATH="$BIN:$LAB/onnxruntime/lib"
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export XDG_DATA_HOME="$W/data"
export XDG_CONFIG_HOME="$LAB/config"
export XDG_CACHE_HOME="$LAB/cache"

cd "$BIN" || exit 1
timeout "$SECS" ./vcmiclient --headless --testmap "$MAPNAME" \
    --ai "$AIONE" --ai "$AITWO" --nointro --disable-video --savefrequency 1 \
    > "$W/client.log" 2>&1
echo "exit=$?"
echo "--- markers ---"
grep -iE "not found|Disaster|Starting debug|Turn|victory|defeat|AI.*turn|save" "$W/client.log" | tail -20
echo "--- saves ---"
ls -la "$W/data/vcmi/" 2>/dev/null | head
find "$W" -name "*.vsv" -o -name "*.vlg" 2>/dev/null | head
