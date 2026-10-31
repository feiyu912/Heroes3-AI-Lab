#!/usr/bin/env bash
set -uo pipefail
BIN=/root/heroes3-ai-lab/src/gym/vcmi/rel/bin
echo "=== frozen battle binaries (baseline) ==="
sha256sum "$BIN"/libvcmi.so "$BIN"/libmlserverplugin.so "$BIN"/vcmiserver "$BIN"/vcmiclient \
          "$BIN"/libmlclient.so "$BIN"/connector_v15.so 2>/dev/null
echo "=== disk ==="
df -h /root /mnt/g | tail -3
echo "=== memory ==="
free -g
echo "=== git repo ==="
cd /root/heroes3-ai-lab/src/gym || exit 1
git rev-parse --short HEAD 2>/dev/null || echo "not a git repo"
git -C vcmi rev-parse --short HEAD 2>/dev/null || echo "vcmi not a git repo"
echo "=== source size ==="
du -sh /root/heroes3-ai-lab/src/gym/vcmi 2>/dev/null
echo "=== cmake/ninja ==="
cmake --version | head -1; ninja --version
echo "=== cmake cache ML option ==="
grep -E "^ENABLE_ML|^CMAKE_BUILD_TYPE|^CMAKE_INSTALL_PREFIX" /root/heroes3-ai-lab/src/gym/vcmi/rel/CMakeCache.txt
