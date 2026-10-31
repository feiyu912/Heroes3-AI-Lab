# Prepared final CPU review

This is a new subdirectory outside the frozen training inputs. Nothing here changes the running controller/trainer/PLAN. `audit_final.py` refuses absent/failed/incomplete RESULT or missing either update31..60 arm or any of six final DEV reports. It has not audited the live experiment as final.

After root reports actual terminal completion, run once with a fresh output directory:

```
wsl -- env PYTHONPATH=/root/heroes3-ai-lab/src/gym:/mnt/g/Heroes3-AI-Lab/research LD_LIBRARY_PATH=/root/heroes3-ai-lab/src/gym/vcmi/rel/bin:/root/heroes3-ai-lab/onnxruntime/lib /root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/battle-training-continuation-20261020/final-independent-01/audit_final.py --out /mnt/g/Heroes3-AI-Lab/experiments/battle-training-continuation-20261020/final-independent-01/actual-review-01
```

CPU review scope: current494 source inputs; both initial restoration identities/allRNG flags and matching parent model/Adam digests; same configs except arm/LR/output paths; all60 saved checkpoint/rollout SHA/boundaries, ordered Adam/moments and perparameter≤cumulative counts; stage steps separately from3840 historical; released parameter deltas and frozen weights; same240 TRAIN cells each64 rows per arm, actual terminal strata and phase-close/GAE bootstrap; final models/Adam CPU load. It does not repeat CUDA restore or full onpolicy probability evaluation.

All96 DEV raw results/logs and every actual predecision graph/logits/probability/argmax action plus synchronous native step return are checked, including adjacent next-observation continuity and aggregate digest/outcome/action-type reconstruction. Parent32 games are shared, not duplicated into128 purported independent games. The64 paired comparisons use max lengths rather than zip, report first public graph/action difference including EOF, and do not claim complete-world/NPC determinism or causal skill improvement.

`PREPARATION_CPU_CHECKS.json` only covers syntax and temporary fake incomplete-result refusals. Actual native/learning qualification remains false until the final audit runs on completed evidence. Preserve raw step/checkpoint files until audit and archive finish.
