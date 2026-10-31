#!/usr/bin/env bash
# Try the resource-name forms VCMI may expect for --testmap.
set -uo pipefail
LAB=/root/heroes3-ai-lab
BIN=$LAB/src/gym/vcmi/rel/bin
W=$LAB/workers/adv-smoke3

export LD_LIBRARY_PATH="$BIN:$LAB/onnxruntime/lib"
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export XDG_DATA_HOME="$W/data"
export XDG_CONFIG_HOME="$LAB/config"
export XDG_CACHE_HOME="$LAB/cache"
cd "$BIN" || exit 1

for M in "Maps/diverse-192" "Maps/diverse-192.vmap" "maps/diverse-192.vmap"; do
  echo "=== testmap=$M ==="
  timeout 40 ./vcmiclient --headless --testmap "$M" --ai Nullkiller2 --ai Nullkiller2 \
      --nointro --disable-video > "$W/try.log" 2>&1
  grep -a -m3 -iE "Disaster|Reason:|Starting debug|Turn 1|victory|defeat|game started" "$W/try.log"
done
