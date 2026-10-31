# Reproduce the actual learning procedure

Use WSL Ubuntu-22.04 with the existing /root/heroes3-ai-lab CPU/GPU virtual environments and qualified typed-director-terminal-drain-capsule-03. G workspace is /mnt/g/Heroes3-AI-Lab. Do not overwrite previous output directories or edit frozen dependencies. Exactly one GPU learner, GPU lock before pool lock; existing scripts enforce both.

The first registered batch failed a strict native audit, so the default seedbase2000 is not the successful training batch. Both attempts and all original logs remain evidence. The successful batch used this explicit command (choose a genuinely new output directory):

```sh
/usr/bin/python3 /mnt/g/Heroes3-AI-Lab/experiments/strategic-learning-mainline-20261020/native-pipeline/run_pipeline.py \
  --seed-base 2026102200 --execute \
  --out /root/heroes3-ai-lab/evaluations/strategic-mainline-temperature2-reproduction-NEW
```

It collects both TRAIN maps x both roles x EmptyAI/Nullkiller2 under exactly one frozen T2 parent, applies the unchanged v4 native auditor and exact CUDA sampler replay, then initializes a new Adam and performs one unchanged episode-balanced PPO update. It never trains from six valid cells or treats an invalid/timeout game as loss. Parent historical164 steps are lineage, not continued Adam state.

Saved model and recovery proof from the actual completed run:

- trained-cuda-01/update-1.pt SHA bb3417624bdb25023e1dbbb2e8eb49de140f2a4264c9de0444659f2b953803cc
- checkpoint-cuda-audit-01/AUDIT.json: actual CUDA model/Adam/RNG restore,5 invalid-resume checks,0 audit optimizer steps.
- learned-policy-comparison-01/AUDIT.json: same-state policy differences, not ability evidence.

The independent DEV procedure uses T2 initialization as baseline, trained checkpoint as candidate and fixed seeds2100..2107, with CPU argmax and no coordinate proxy:

```sh
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-learning-mainline-20261020/evaluate_dev.py \
  --baseline /mnt/g/Heroes3-AI-Lab/experiments/strategic-learning-mainline-20261020/temperature-initialization-01/temperature-2-initialization.pt \
  --candidate /mnt/g/Heroes3-AI-Lab/experiments/strategic-learning-mainline-20261020/trained-cuda-01/update-1.pt \
  --out /root/heroes3-ai-lab/evaluations/strategic-mainline-temperature2-dev-reproduction-NEW
```

Actual completed DEV was6/8 versus6/8, all pair outcomes unchanged. One win became much slower; no superiority was certified and the accepted model was not replaced. Two DEV maps were historically seen, final-test maps untouched. Never add DEV labels to training admissions.

Reproducibility means inspectable frozen sources, seeds, inputs, saved states and exact admission/recovery checks. Full newly rerun native/NK hidden-world ordering is not proven deterministic; do not guarantee identical games, byte-identical checkpoint containers, counts or wins on a fresh rerun. Any new audit failure must remain visible rather than be silently retried or admitted.
