# Multihero mechanism probe v2 — audit recovery

Status: **engineering audit recovery, not a new mechanism and not a strategic-strength result.**
No C++ source, capsule binary, model, or frozen v1 input was changed. This version uses the
already-built `multihero-capsules-03` capsule and runs fresh native close/transfer probes with a
corrected, source-derived query-closure gate. No optimizer, PPO sample, GPU learner, or game score is
involved.

## Why v2 exists

The v1 raw runs `multihero-probe-close-04` and `multihero-probe-transfer-01` contain real native
ExchangeDialog callbacks, successful close ACKs, and (for transfer) a successful ArrangeStacks ACK.
However, their stored `AUDIT.json` files report `engineering_pass=true` even though the current v1
`audit_run.py` requires an `exchange_query_resolved` event that is absent from the raw `probe.jsonl`.
Re-running the current v1 auditor on both runs fails:

```text
AssertionError('Exactly one exchange_query_resolved required')
```

The source explains the absence: `CGarrisonDialogQuery` derives directly from `CDialogQuery` and has
no `onRemoval` override that calls `CGameHandler::sendQueryResolved`. The only `sendQueryResolved`
calls in `MapQueries.cpp` belong to the level-up and commander-level-up queries. Therefore the v1
audit's `exchange_query_resolved` requirement was **invalid for this dialog class**, and the stored
v1 `AUDIT.json` passes are not usable as independent evidence. They are preserved, not edited.

## Corrected closure evidence

For this dialog class, native closure is proven by the sequence:

1. a real `heroExchangeStarted(hero1, hero2, queryID)` callback from an actual native visit;
2. the actual `QueryReply` for that query produces a successful `PackageApplied` (`close_ack`,
   `result=1`) and leaves no pending query/request;
3. a subsequent native `EndTurn` is sent and receives a successful `PackageApplied` (`endturn_ack`,
   `result=1`).

The server's `CGameHandler::queryReply` verifies that the answered query is the player's top query,
sets the reply, and pops it. A failed or still-blocking query would reject the subsequent EndTurn.
The v2 auditor requires all of those raw events, plus move ACKs, transfer conservation for
`transfer-close`, no native rejection, and no action after the proved EndTurn boundary. It does not
require a nonexistent `QueryResolved` event. This is a corrected gate, not a silently relaxed one:
the old passing audit is invalidated and the old negative/unhandled result remains negative.

## Results

`NATIVE_RESULTS.md` records the exact evidence and hashes. The qualified v2 runs are
`multihero-probe-close-v2-04` and `multihero-probe-transfer-v2-01`; both pass the source-derived
v2 gate. The earlier `close-v2-01`/`-02` startup failures and `close-v2-03` mutable-config audit
failure are preserved, not counted. The v1 raw evidence and its invalid `AUDIT.json` passes remain
in `../multihero-mechanism-probe-v1/native-evidence-01/`.

## Fresh runs

`run_probe_v2.py` is a copy of the v1 runner with the completion criterion changed to the sequence
above. It still acquires the GPU learner then pool locks, verifies the v2 capsule attestation and
loaded library mappings, forbids `LAB_ADV_AGENT_DIR`, starts exactly one native process group, and
writes only to a new `--out` directory. It also snapshots the launch-time config in
`initial-config/` because VCMI rewrites the live config during startup.

```text
python3 run_probe_v2.py --capsule /root/heroes3-ai-lab/evaluations/multihero-capsules-03/close-only \
  --variant close-only --out /root/heroes3-ai-lab/evaluations/multihero-probe-close-v2-04 --execute

python3 run_probe_v2.py --capsule /root/heroes3-ai-lab/evaluations/multihero-capsules-03/transfer-close \
  --variant transfer-close --out /root/heroes3-ai-lab/evaluations/multihero-probe-transfer-v2-01 --execute
```

The runner writes `AUDIT_V2.json`. The v2 auditor reads raw events and trace state and writes its own
`AUDIT_V2.json`; it never rewrites `probe.jsonl`, `strategy-trace.jsonl`, or `client.log`. Reusing a
preserved v1 plan is only possible if that plan's frozen inputs are still intact; the v1 `AUDIT.json`
itself is not evidence.

## Scope and limits

- This certifies query closure and one conservative merge/swap transfer only.
- It does not certify multihero scheduling, courier strategy, town delivery, defense allocation, or
  full-game strength.
- A timeout, missing ACK, native rejection, transfer conservation failure, or extra action after the
  boundary remains an engineering failure in its own new directory.
- The v1 `close-01`/`close-02` startup failures, `close-03` frozen-input/timeout failure, and
  `unhandled-01` negative control remain in the v1 evidence and are not overwritten.
