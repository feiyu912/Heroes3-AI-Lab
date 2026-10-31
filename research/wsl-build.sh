#!/usr/bin/env bash
set -euo pipefail
lab_root=/root/heroes3-ai-lab
lab_gym=$lab_root/src/gym
lab_cmake=$lab_root/python-packages/cmake/data/bin/cmake
"$lab_cmake" --build "$lab_gym/vcmi/rel" --target mlclient vcmiclient vcmiserver --parallel 4
"$lab_cmake" -S "$lab_gym/vcmi_gym/connectors" -B "$lab_gym/vcmi_gym/connectors/rel" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE='-O2 -DNDEBUG' \
    -DLIBMLCLIENT="$lab_gym/vcmi/rel/bin/libmlclient.so"
"$lab_cmake" --build "$lab_gym/vcmi_gym/connectors/rel" --parallel 2
