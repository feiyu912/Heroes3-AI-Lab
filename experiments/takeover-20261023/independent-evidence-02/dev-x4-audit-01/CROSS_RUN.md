# Cross-run DEV comparison

- Unchanged arms byte-identical across the two runs: **True**
- Prior zero-updated wins: 4/8; x4 zero-updated wins: 4/8
- Cross-run zero-updated net wins: 0
- Within-current zero-update net wins: 0
- Prior zero-updated recruits/quantity: 422/3124
- x4 zero-updated recruits/quantity: 1673/3945

## Per-cell zero-updated outcomes

| pair | map | opponent | role | prior | x4 | change |
|---:|---|---|---:|---:|---:|---|
| 0 | takeover-v2-dev-01-river | EmptyAI | 0 | 1 | 1 | unchanged |
| 1 | takeover-v2-dev-01-river | EmptyAI | 1 | 1 | 1 | unchanged |
| 2 | takeover-v2-dev-01-river | Nullkiller2 | 0 | 0 | 0 | unchanged |
| 3 | takeover-v2-dev-01-river | Nullkiller2 | 1 | 0 | 0 | unchanged |
| 4 | takeover-v2-dev-02-reserves | EmptyAI | 0 | 1 | 1 | unchanged |
| 5 | takeover-v2-dev-02-reserves | EmptyAI | 1 | 1 | 1 | unchanged |
| 6 | takeover-v2-dev-02-reserves | Nullkiller2 | 0 | 0 | 0 | unchanged |
| 7 | takeover-v2-dev-02-reserves | Nullkiller2 | 1 | 0 | 0 | unchanged |

The unchanged control arms being byte-identical makes evaluator drift an unlikely explanation for the zero-updated difference. It does not make the two training runs equal-Adam or establish a population effect.
