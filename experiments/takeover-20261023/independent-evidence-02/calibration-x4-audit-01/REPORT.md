# Independent calibration raw audit

All 12 registered cells were read from disk and checked against `RESULT.json`, `MAP_MANIFEST.json`, the frozen initialization and each cell's native plan/execution/raw audit.

- Wins: x1 `0/4`, x2 `1/4`, x4 `2/4`
- Selected multiplier: `4`
- Every audit SHA, per-file raw SHA and single completed `game_over` matched.
- Zero GPU runs, zero optimizer steps, zero training rows, no DEV/final-test path.

This is TRAIN-only difficulty selection evidence, not an independent win-rate claim or expert demonstration.
