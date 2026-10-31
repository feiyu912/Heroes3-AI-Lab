#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
runtime=/root/heroes3-ai-lab-events-v2
exp=/mnt/g/Heroes3-AI-Lab/experiments/human-tactics-visible-exchange-v1-pilot02
worker=${LAB_WORKER_ROOT:-$runtime/workers/visible-exchange-${BASHPID}-$(date +%s%N)}
python=/root/heroes3-ai-lab/venv/bin/python
"$python" "$exp/prepare_events_worker.py" "$worker"
export PYTHONPATH="$runtime/src/gym:$exp:/mnt/g/Heroes3-AI-Lab/research"
export LD_LIBRARY_PATH="$runtime/src/gym/vcmi/rel/bin:$runtime/onnxruntime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export XDG_DATA_HOME="$worker/data"
export XDG_CONFIG_HOME="$worker/config"
export XDG_CACHE_HOME="$worker/cache"
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
cd "$runtime/src/gym"
exec "$python" "$@"
