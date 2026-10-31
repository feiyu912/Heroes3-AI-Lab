# Terminal-credit native recovery package 01

This package continues the stopped
`battle-terminal-credit-native-20261023` run under
`RECOVERY_PROTOCOL.md`. The historical package and its evaluation evidence are
read-only inputs.

Use `recover.py`, not the old package's `run.py` (which is intentionally not
copied here):

```bash
PYTHONPATH=/mnt/g/Heroes3-AI-Lab/research \
/root/heroes3-ai-lab/gpu-venv/bin/python \
/mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-recovery-20261023-01/recover.py \
--out /root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-01 \
--execute --evaluate
```

Without `--execute` it only writes `FREEZE.json` and `PLAN.json`. With
`--execute` it acquires the GPU learner lock then the pool lock, holds them for
all training stages, releases them before the optional DEV stage, and preserves
raw output on any failure.

The recovery schedule is:

- independent read-only audit of old `control-phase-1` and update-64;
- candidate phase 1 from candidate update-62;
- paired phases 2 and 3 from the accepted boundaries;
- optional pre-registered 96-game DEV.

The source difference from the historical package is limited to
`learner_impl.py`'s post-update resource check (RAM guard kept, swap recorded
instead of stopping, actual values included in assertion messages). All model,
target, optimizer, curriculum, audit and evaluation code is otherwise the same.
No old evidence is edited.
