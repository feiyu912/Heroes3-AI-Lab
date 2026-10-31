#!/usr/bin/env bash
set -euo pipefail
lab_root=/root/heroes3-ai-lab
lab_gym=$lab_root/src/gym
export PYTHONPATH="$lab_gym"
export LD_LIBRARY_PATH="$lab_gym/vcmi/rel/bin:$lab_root/onnxruntime/lib"
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
cd "$lab_gym"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
timeout 60 gdb -batch -ex 'set pagination off' -ex run -ex 'bt 15' \
    -ex 'x/8i $pc-16' -ex 'info registers rax rdi rip' -ex 'disassemble ML::shutdown_vcmi()' \
    --args "$lab_root/venv/bin/python" /mnt/g/Heroes3-AI-Lab/research/battle-smoke.py \
    --episodes 1 --output /mnt/g/Heroes3-AI-Lab/research/smoke-debug.json
