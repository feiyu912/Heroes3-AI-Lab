# Same-window CPU DEV entry

Ready for root review; no native/GPU/optimizer run was started. Only this new subdirectory was written. `collect_cpu.py` is a minimal diff from the frozen root collector, uses the frozen schema5 CPU broker and retains all raw/runtime/script/ACK gates. Root audit_game_v6.py remains unchanged. Models, maps, seeds, ordering and capsule are fixed in PLAN.md; there is no proxy or clearance decision path.

CPU_REPORT.json passed: Python syntax/imports, plan with eight pairs / sixteen games / 356 frozen inputs, unchanged parent source SHAs, both actual checkpoints loaded on CPU and argmax computed on one archived real training request. This is preparation only, not DEV execution or an ability result.

Root command after review (omit `--execute` for a fresh plan only):

```bash
/usr/bin/python3 /mnt/g/Heroes3-AI-Lab/experiments/strategic-learned-economy-run-v1/dev-tools/evaluate_dev.py \
  --baseline /mnt/g/Heroes3-AI-Lab/experiments/strategic-learned-economy-policy-v1/cpu-01/build-initialization.pt \
  --candidate /root/heroes3-ai-lab/evaluations/strategic-learned-build-training-01/update-01/update-1.pt \
  --out /root/heroes3-ai-lab/evaluations/strategic-learned-build-dev-01 --execute
```

Root keeps the original GPU/pool lock discipline even though policy inference here is CPU only. Each game is audited with unchanged strict run-v1 build evidence and whole-game termination proof. Invalid arms abort the batch, preserve raw and remain unscored. No admission or training call occurs. All Python/PLAN inputs are frozen before the first arm; do not edit running source. Final-test maps are untouched.
