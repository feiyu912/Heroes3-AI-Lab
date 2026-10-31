# Implementation correction 01 — vector worker `lab-env.py` path

Date: 2026-10-23. Status: pre-execution correction; no native game, GPU
operation or optimizer step was performed to discover or validate it.

## Defect

`recorded_vector.py` was copied from `/mnt/g/Heroes3-AI-Lab/research/vector_env.py`
by `derive.py`. The source file lives beside `research/lab-env.py`, so it loads
the environment module with:

```python
Path(__file__).with_name('lab-env.py')
```

The copy lives in this experiment directory, where no `lab-env.py` exists.
The first native worker would therefore fail at module load before any battle
step. Reproduction with the CPU-only interpreter:

```
resolved /mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/lab-env.py exists False
FileNotFoundError [Errno 2] No such file or directory: ...
```

The CPU checks in `cpu-final-04` did not catch this because they exercise the
real collector over an in-process synthetic `FixtureVector`, not a spawned
native worker.

## Correction

The derivation now rewrites only that path to the accepted frozen source:

```python
Path('/mnt/g/Heroes3-AI-Lab/research/lab-env.py')
```

`research/lab-env.py` SHA
`bdb325ee5cad7d5df952a35f7d357ef9f3bad4d624fe5bd2233b46a11f0b0dee`
was already part of the historical frozen input set (it is included by the
parent package's `inputs()` through `research/*.py`). No historical source,
binary, model or evidence file was edited.

`derive.py` was updated so the correction is reproducible, then re-run. All
other derived files were byte-identical; only `recorded_vector.py` changed:

| File | Before | After |
|---|---|---|
| `recorded_vector.py` | `353d3bfe2cf47a7fc19c5035dadd858019054b0442d07e35eaa19aa0c1449ca3` | `f6395c1b083255c2a8e367024403a6627bb3ebc0cc2cbfe3792cea879110637f` |
| `derive.py` | `583b261805c9b7eb852d2625dd183458910ab82ec723afe523d47b5ee145cfed` | `835e9ce26f4bfde1ef8883f94c1e9f9ef43f7a6cd9f2dfa9affa8483270b06f3` |

## Re-validation

- `cpu-final-05/AUDIT.json`: CPU restore, production target cases, real NN
  collector over marked synthetic fixtures, private suffix RNG and auditor
  rejection of synthetic evidence. `new_native_games=0`, `GPU_operations=0`,
  `optimizer_steps=0`.
- `plan-final-05/PLAN.json`: plan-only freeze of the corrected sources and this
  note. The freeze contains the corrected `recorded_vector.py` hash and the
  accepted `research/lab-env.py` hash; every frozen entry re-hashes exactly.
  (`plan-final-04` was the same check before this note existed.)
- Import probe under the worker environment (`vcmi_gym` on `PYTHONPATH`):
  `research/lab-env.py` imports and `torch` is not imported by `vcmi_env` /
  `battle_features`.

## Superseded artifacts

`cpu-final-04` and `plan-final-03` remain on disk unchanged. They describe the
uncorrected sources and are not evidence for the executed package. The
authoritative pre-execution checks for the next native attempt are
`cpu-final-05` and `plan-final-04`.

This correction does not change the registered scientific factor, the parent
checkpoint, the curriculum, the budgets, the target rule or the DEV design.
