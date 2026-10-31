#!/usr/bin/env bash
set -euo pipefail
exp=/mnt/g/Heroes3-AI-Lab/experiments/human-tactics-events-v3/curriculum-v2
for scenario in 0 1; do
  for role in attacker defender; do
    for seed in 2026101811 2026101812; do
      for policy in teacher wait-bait; do
        output="$exp/runs/train/${scenario}-${role}-${seed}-${policy}.json"
        if [[ -e "$output" ]]; then
          /root/heroes3-ai-lab/venv/bin/python -c 'import json,sys; r=json.load(open(sys.argv[1])); assert r.get("completed") and r.get("terminated") and not r.get("truncated")' "$output"
          continue
        fi
        bash "$exp/run-events-lab.sh" "$exp/run_episode.py" --scenario "$scenario" --role "$role" --seed "$seed" --policy "$policy" --output "$output"
      done
    done
  done
done
