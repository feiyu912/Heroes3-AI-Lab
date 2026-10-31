# Real CPU simulation throughput audit

This is a native CPU throughput measurement with scripted DirectorAI and native battles. It does not demonstrate parallel PPO, GPU simulation, learned strategic improvement, or 204 independent evaluation games.

| Batch | Slots | Valid jobs | Simultaneous native/worker pairs | Games/s | Peak RSS GB | Peak PSS GB | Swap |
|---|---:|---:|---:|---:|---:|---:|---:|
| native-01 | 1 | 4 | 1 | 0.400 | 0.140 | 0.132 | 0 |
| native-01 | 2 | 8 | 2 | 0.751 | 0.255 | 0.210 | 0 |
| native-02 | 1 | 4 | 1 | 0.402 | 0.143 | 0.135 | 0 |
| native-02 | 2 | 8 | 2 | 0.753 | 0.253 | 0.208 | 0 |
| native-02 | 4 | 16 | 4 | 1.394 | 0.498 | 0.373 | 0 |
| native-02 | 8 | 32 | 8 | 2.476 | 0.979 | 0.704 | 0 |
| native-02 | 12 | 48 | 12 | 3.424 | 1.486 | 1.052 | 0 |
| native-02 | 24 | 96 | 24 | 5.475 | 2.807 | 1.910 | 0 |

Audit passed: True. Every native log/trace hash, per-job frozen input and current protocol input was recomputed. Stage result and resource-sample SHA256 values and exact simultaneous-process witnesses are in AUDIT.json.

Concurrency is established by matching sampled live PIDs to per-job native PID files, with an equal number of separate worker sessions present at the same sample. The 24-slot run contains a sample with 24 native processes and 24 worker sessions simultaneously; it is not merely a queue length.

Both real batches recorded pool exclusion and no remaining batch processes; the audit independently found no processes carrying either completed batch token. Historical lock ownership follows the frozen FD/inode validation implementation and successful worker completion; this audit did not retroactively observe kernel locks during those runs. The current lock probe is separately recorded.

The four fixed map/role/seed workloads repeat intentionally. Across both real batches and all scales, winner, calendar turns, move count, full state-trace SHA, decision-trace SHA and target-diagnostic SHA match for every repetition of a workload. This supports deterministic workload comparability, not independent evidence of policy strength.

Samples are approximately every 200 ms; peaks are sampled, RSS counts shared pages multiple times, PSS is reported separately. Startup, file integrity checks, logging and cleanup are included. The observed 24-slot result supports this bounded workload on this machine, not arbitrary maps or indefinitely sustained 24-environment training. Synthetic results remain in separate synthetic-* directories.

No frozen measurement source or input was edited by this audit.
