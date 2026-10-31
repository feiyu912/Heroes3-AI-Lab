# BC pipeline smoke test (2026-10-31)

This is an engineering smoke test, not a training result and not a model claim.

## Data used

`experiments/takeover-20261023/active-learning-delivery-01/native-study/control/cell-00/admitted/samples.jsonl`
(799 admitted decisions from one EmptyAI game; SHA-256
`fcd0b54d0d5a69ad20647813b18cfa855873ba055982fb1032064e9e3fd616a3`).

`validate_dataset.py` result:

```json
{
  "passed": true,
  "unique_decisions": 799,
  "split_counts": {"unspecified": 799},
  "action_counts": {"build": 11, "move": 483, "recruit": 218, "end_turn": 87}
}
```

## Training smoke

- first 200 records, one episode, no validation split, CPU, 1 epoch, batch 32;
- masked candidate cross-entropy, action-type weights, value loss disabled by
  absent `return` targets;
- checkpoint saved and reloaded; forward logits/value finite;
- train top-1 0.585 on the 200-record fit set.

This only proves the data path, loss, checkpoint and reload work.  It does **not**
prove strategic strength; the data is not an expert dataset, and the episode is
the already-solved EmptyAI case.

## Next

Wait for the externally prepared teacher/human dataset, validate it with
`--require-split --min-samples 10000`, then train a real BC checkpoint and run
paired native evaluation before any PPO integration.
