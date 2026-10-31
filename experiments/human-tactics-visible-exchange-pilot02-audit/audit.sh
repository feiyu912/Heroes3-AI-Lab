#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYTHONPATH=/root/heroes3-ai-lab-events-v2/src/gym
export LD_LIBRARY_PATH=/root/heroes3-ai-lab-events-v2/src/gym/vcmi/rel/bin:/root/heroes3-ai-lab-events-v2/onnxruntime/lib
exec /root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-visible-exchange-pilot02-audit/audit.py
