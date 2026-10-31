# Terminal-credit recovery 02

This package continues the frozen recovery-01 training from both update-66
boundaries after the recovery-01 `control-phase-3` pre-phase swap stop. It does
not contain a second copy of the training code. `recover_02.py` invokes the
frozen training package:

`G:\Heroes3-AI-Lab\experiments\battle-terminal-credit-native-recovery-20261023-01`

The only new behavior is an external, bounded pre-stage readiness wait that
uses the same thresholds and records all resource values. The frozen training
guard remains in force and is not edited.

Plan only:

```bash
/root/heroes3-ai-lab/gpu-venv/bin/python \
/mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-recovery-20261023-02/recover_02.py \
--out /root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-02
```

Execute phase 3 and the DEV:

```bash
PYTHONPATH=/mnt/g/Heroes3-AI-Lab/research \
/root/heroes3-ai-lab/gpu-venv/bin/python \
/mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-recovery-20261023-02/recover_02.py \
--out /root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-02 \
--execute --evaluate
```

Evidence preservation:

- recovery-01 evaluation directory is not modified;
- the failed control-phase-3 stage is not retried or rewritten;
- each new stage has its own `RESULT.json`, `PROGRESS.json`, checkpoints and
  `AUDIT.json`;
- `WAIT-<stage>.json` records the swap wait;
- the new controller writes `RESULT.json` even on failure.
