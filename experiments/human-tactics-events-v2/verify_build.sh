#!/usr/bin/env bash
# events-v2: verify the isolated runtime carries the native-event extension.
set -euo pipefail
SO=/root/heroes3-ai-lab-events-v2/src/gym/vcmi/rel/bin/libmlclient.so
OBJ=/root/heroes3-ai-lab-events-v2/src/gym/vcmi/rel/AI/MMAI/CMakeFiles/MMAI.dir/BAI/v15/state_v15.cpp.o

echo "== object symbols (patched code compiled) =="
nm -C "$OBJ" | grep -cE 'MMAI::BAI::V15::State::onBattleAttack|MMAI::BAI::V15::State::onActionStarted' || true

echo "== libmlclient.so exported symbols =="
nm -D -C "$SO" 2>/dev/null | grep -E 'getBattleEvents|onBattleAttack' | head -5 || echo "(none in dynsym)"

echo "== original lib untouched (Oct 14 21:29 build) =="
ls -la /root/heroes3-ai-lab/src/gym/vcmi/rel/bin/libmlclient.so
ls -la "$SO"
