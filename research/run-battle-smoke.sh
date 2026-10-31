#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
lab_root=/root/heroes3-ai-lab
lab_gym=$lab_root/src/gym
lab_worker_root=${LAB_WORKER_ROOT:-$lab_root/workers/manual}
"$lab_root/venv/bin/python" /mnt/g/Heroes3-AI-Lab/research/prepare-worker.py "$lab_worker_root"
export PYTHONPATH="$lab_gym"
export LD_LIBRARY_PATH="$lab_gym/vcmi/rel/bin:$lab_root/onnxruntime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export XDG_DATA_HOME="$lab_worker_root/data"
export XDG_CONFIG_HOME="$lab_root/config"
export XDG_CACHE_HOME="$lab_root/cache"
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
"$lab_root/venv/bin/python" /mnt/g/Heroes3-AI-Lab/research/make-smoke-map.py
cd "$lab_gym"
"$lab_root/venv/bin/python" -c 'from vcmi_gym.connectors.rel import connector_v15; print("Connector import passed", flush=True)'
if [[ ${1:-} == --benchmark ]]; then
    shift
    timeout 60 "$lab_root/venv/bin/python" /mnt/g/Heroes3-AI-Lab/research/benchmark-worker.py "$@"
else
    timeout 180 "$lab_root/venv/bin/python" /mnt/g/Heroes3-AI-Lab/research/battle-smoke.py "$@"
fi
