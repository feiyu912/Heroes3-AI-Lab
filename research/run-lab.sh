#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
lab_root=/root/heroes3-ai-lab
lab_worker_root=${LAB_WORKER_ROOT:-$lab_root/workers/lab-manual}
"$lab_root/venv/bin/python" /mnt/g/Heroes3-AI-Lab/research/prepare-worker.py "$lab_worker_root"
export PYTHONPATH="$lab_root/src/gym:/mnt/g/Heroes3-AI-Lab/research"
export LD_LIBRARY_PATH="$lab_root/src/gym/vcmi/rel/bin:$lab_root/onnxruntime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
if [[ ${LAB_NATIVE_ONNX_CUDA:-0} == 1 ]]; then
    export LD_LIBRARY_PATH="${LAB_NATIVE_ONNX_LIBRARY:?Missing native GPU runtime directory}:$LD_LIBRARY_PATH"
fi
export XDG_DATA_HOME="$lab_worker_root/data"
export XDG_CONFIG_HOME="$lab_root/config"
export XDG_CACHE_HOME="$lab_root/cache"
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$lab_root/src/gym"
exec "${LAB_PYTHON:-$lab_root/venv/bin/python}" "$@"
