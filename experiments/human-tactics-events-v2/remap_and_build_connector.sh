#!/usr/bin/env bash
# events-v2: remap the copied connector build dir and rebuild connector_v15.so
# against the isolated runtime's libmlclient.
set -euo pipefail
SRC_OLD=/root/heroes3-ai-lab/src/gym
SRC_NEW=/root/heroes3-ai-lab-events-v2/src/gym
REL=/root/heroes3-ai-lab-events-v2/src/gym/vcmi_gym/connectors/rel

echo "remapping connector build files..."
find "$REL" -type f \( -name 'CMakeCache.txt' -o -name 'build.ninja' -o -name 'rules.ninja' \
  -o -name 'cmake_install.cmake' -o -name '*.cmake' \) -print0 \
  | xargs -0 sed -i "s|${SRC_OLD}|${SRC_NEW}|g"
rm -f "$REL/.ninja_deps" "$REL/.ninja_log"

echo "rebuilding connector (ninja)..."
cd "$REL"
ninja 2>&1 | grep -vE '^\[[0-9]+/[0-9]+\]' | tail -20

echo "verify:"
ls -la "$REL/connector_v15.so"
nm -C "$REL/connector_v15.so" 2>/dev/null | grep -c getBattleEvents || echo "(0 dynsym hits; checking symtab)"
nm -C "$REL/connector_v15.so" 2>/dev/null | grep -E 'buildObsDict' | head -2
