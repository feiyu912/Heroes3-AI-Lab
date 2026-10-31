#!/usr/bin/env bash
# events-v2: CUDA BC launcher (gpu-venv), single entry to avoid MSYS path mangling.
set -euo pipefail
export LAB_PYTHON=/root/heroes3-ai-lab/gpu-venv/bin/python
bash /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v2/run-events-lab.sh \
  /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v2/bc_train_events.py "$@"
