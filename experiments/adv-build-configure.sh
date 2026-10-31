#!/usr/bin/env bash
# Isolated ENABLE_ML=OFF build for the adventure/strategic layer.
# The frozen battle build in vcmi/rel is never touched: source is copied, build dir is separate,
# install prefix is separate. All output paths are under the -adv suffix.
set -uo pipefail
LAB=/root/heroes3-ai-lab
SRC_OLD=$LAB/src/gym/vcmi
SRC=$LAB/src/vcmi-adv
BUILD=$LAB/src/vcmi-adv-build
PREFIX=$LAB/install-adv

echo "=== sizes ==="
du -sh "$SRC_OLD/rel" 2>/dev/null
du -sh "$SRC_OLD" 2>/dev/null

if [ ! -d "$SRC" ]; then
  echo "=== copying source (excluding build dir) ==="
  mkdir -p "$SRC"
  rsync -a --exclude 'rel' --exclude '.git' --exclude '*.o' "$SRC_OLD"/ "$SRC"/
fi
du -sh "$SRC"

echo "=== configure ==="
# MMAI's CMakeLists requires 3.24+, so use the same cmake the frozen build used.
CMAKE=/root/heroes3-ai-lab/python-packages/cmake/data/bin/cmake
"$CMAKE" --version | head -1
"$CMAKE" -S "$SRC" -B "$BUILD" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=/usr/bin/c++ \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DENABLE_ML=OFF \
  -DONNXRUNTIME_ROOT=/root/heroes3-ai-lab/onnxruntime \
  -DONNXRUNTIME_INCLUDE_DIR=/root/heroes3-ai-lab/onnxruntime/include \
  -DONNXRUNTIME_LIBRARY=/root/heroes3-ai-lab/onnxruntime/lib/libonnxruntime.so \
  -DENABLE_BATTLE_AI=ON \
  -DENABLE_STUPID_AI=ON \
  -DENABLE_MMAI=ON \
  -DENABLE_MMAI_TEST=OFF \
  -DENABLE_CLIENT=ON \
  -DENABLE_SERVER=ON \
  -DENABLE_EDITOR=OFF \
  -DENABLE_LAUNCHER=OFF \
  -DENABLE_LOBBY=OFF \
  -DENABLE_TEST=OFF \
  -DENABLE_VIDEO=OFF \
  -DENABLE_DISCORD=OFF \
  -DENABLE_GOLDMASTER=OFF \
  -DENABLE_MINIMAL_LIB=OFF \
  -DENABLE_MONOLITHIC_INSTALL=OFF \
  -DENABLE_SINGLE_APP_BUILD=OFF \
  -DENABLE_STATIC_LIBS=OFF \
  -DENABLE_STRICT_COMPILATION=OFF \
  -DENABLE_TRANSLATIONS=ON \
  -DENABLE_PCH=ON \
  -DENABLE_LTO=OFF \
  -DENABLE_CCACHE=OFF \
  -DENABLE_GITVERSION=OFF \
  -DENABLE_DEBUG_CONSOLE=ON \
  -DENABLE_COLORIZED_COMPILER_OUTPUT=ON \
  2>&1 | tail -25

echo "=== configured ML flag ==="
grep -E "^ENABLE_ML|^ENABLE_MMAI|^ENABLE_NULLKILLER" "$BUILD/CMakeCache.txt"
