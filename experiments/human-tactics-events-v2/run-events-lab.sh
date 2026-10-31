#!/usr/bin/env bash
# events-v2 launcher: same protocol as the frozen research/run-lab.sh, rooted at
# the isolated events-v2 runtime (/root/heroes3-ai-lab-events-v2).
# Shared read-only resources: the shared CPU/CUDA venv interpreters and the
# global resource lock /root/heroes3-ai-lab/evaluations/.pool-lock.
set -euo pipefail
ulimit -c 0
lab_root=/root/heroes3-ai-lab-events-v2
lab_worker_root=${LAB_WORKER_ROOT:-$lab_root/workers/lab-events-manual}
exp_dir=/mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v2

"$lab_root/../heroes3-ai-lab/venv/bin/python" "$exp_dir/prepare_events_worker.py" "$lab_worker_root"

export PYTHONPATH="$lab_root/src/gym:$exp_dir:/mnt/g/Heroes3-AI-Lab/research"
export LD_LIBRARY_PATH="$lab_root/src/gym/vcmi/rel/bin:$lab_root/onnxruntime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export XDG_DATA_HOME="$lab_worker_root/data"
export XDG_CONFIG_HOME="$lab_root/config"
export XDG_CACHE_HOME="$lab_root/cache"
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$lab_root/src/gym"
exec "${LAB_PYTHON:-$lab_root/../heroes3-ai-lab/venv/bin/python}" "$@"
