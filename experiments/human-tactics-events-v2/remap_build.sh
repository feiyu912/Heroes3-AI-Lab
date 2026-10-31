#!/usr/bin/env bash
# events-v2: remap the copied VCMI build dir to the isolated runtime source tree.
# Only text build files are remapped (binary .o files untouched).
# Shared read-only resources (onnxruntime, cmake toolchain) keep pointing
# at the original lab install; nothing under /root/heroes3-ai-lab is written.
set -euo pipefail
SRC_OLD=/root/heroes3-ai-lab/src/gym
SRC_NEW=/root/heroes3-ai-lab-events-v2/src/gym
OLD_INSTALL=/root/heroes3-ai-lab/install
NEW_INSTALL=/root/heroes3-ai-lab-events-v2/install-local
REL=/root/heroes3-ai-lab-events-v2/src/gym/vcmi/rel

echo "remapping build files..."
find "$REL" -type f \( -name 'CMakeCache.txt' -o -name 'build.ninja' -o -name 'rules.ninja' \
  -o -name 'cmake_install.cmake' -o -name '*.cmake' \) -print0 \
  | xargs -0 sed -i "s|${SRC_OLD}|${SRC_NEW}|g; s|${OLD_INSTALL}|${NEW_INSTALL}|g"

echo "deleting stale ninja dep/log (binary formats carry old paths)..."
rm -f "$REL/.ninja_deps" "$REL/.ninja_log"

echo "touching potential consumers of patched MMAI headers..."
cd "$SRC_NEW/vcmi"
find AI/MMAI ML -name '*.cpp' -exec touch {} +
touch lib/callback/AIFactory.cpp server/ML/ServerPlugin.cpp

echo "verifying no leftover original src/gym references in build.ninja..."
if grep -q '/root/heroes3-ai-lab/src/gym' "$REL/build.ninja"; then
  echo "ERROR: build.ninja still references the original tree"; exit 1
fi
echo "remap OK"
