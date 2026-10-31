#!/usr/bin/env bash
set -euo pipefail
lab_root=/root/heroes3-ai-lab
lab_gym=$lab_root/src/gym
lab_cmake=$lab_root/python-packages/cmake/data/bin/cmake
"$lab_cmake" -S "$lab_gym/vcmi" -B "$lab_gym/vcmi/rel" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE='-O2 -DNDEBUG' \
    -DENABLE_ML=ON -DENABLE_MMAI=ON -DENABLE_LAUNCHER=OFF \
    -DENABLE_EDITOR=OFF -DENABLE_TEST=OFF -DENABLE_VIDEO=OFF \
    -DENABLE_DISCORD=OFF -DENABLE_GITVERSION=OFF -DENABLE_SDL3=OFF \
    -DENABLE_PCH=ON -DENABLE_LTO=OFF \
    -DONNXRUNTIME_ROOT="$lab_root/onnxruntime" \
    -DCMAKE_INSTALL_PREFIX="$lab_root/install"
