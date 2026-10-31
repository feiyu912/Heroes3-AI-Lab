# Real CUDA collection capacity

The frozen update-2 candidate completed the authorized 8 → 12 → 24 capacity ladder with one central CUDA model, barrier inference and zero optimizer steps. Every stage passed exact native request consumption, strict execution events, independent raw IO/log re-audit and cleanup. The measured PID witnesses establish simultaneous native processes and their separate workers, rather than queue size.

| Environments | Valid games | Accepted decisions | Wall seconds | Decisions/second | Peak batch RSS / PSS, GB | Simultaneous native / worker |
|---|---:|---:|---:|---:|---:|---:|
| 8 | 8/8 | 2,188 | 35.371 | 61.86 | 0.971 / 0.694 | 8 / 8 |
| 12 | 12/12 | 3,482 | 59.266 | 58.75 | 1.436 / 1.006 | 12 / 12 |
| 24 | 24/24 | 6,237 | 51.957 | 120.04 | 2.750 / 1.855 | 24 / 24 |

All sampled swap usage was zero. Minimum system available RAM was 14.106, 13.765 and 12.872 GB respectively, above the preregistered 20% reserve. Each stage's frozen model/source/binary/config/map inputs were unchanged. Both pool/GPU leases were free at postrun probes and no batch processes remained. GPU allocator sampled maxima were small (24-env allocated 34,665,984 bytes; reserved 39,845,888 bytes), but these are Torch allocator samples, not total hardware VRAM or instantaneous peak. Batch RSS/PSS excludes manager CPU memory; system available RAM includes it.

The 24-env jobs contain eight map/opponent/role cells with three unique seeds per cell, 24 unique seeds total. The 12-env CLI workload has eight train01 jobs and four train02 jobs and is intentionally reported only as engineering workload. All games use training maps and the fixed learned checkpoint; these jobs are not independent capability evaluation or additional training.

The first two stages wrote hot output on `/mnt/g`; the last stage used Linux output `/root/heroes3-ai-lab/evaluations/strategic-vector-capacity-learned-01/scale-24` without changing the collector or inputs, retaining the 120-second per-game budget. Forward-and-sampling time was 4.521/59.266 seconds (7.63%) at 12 env and 6.682/51.957 seconds (12.86%) at 24 env. Most time was outside measured forward calls. Workload and output location both changed, so the throughput difference does not isolate NTFS overhead or establish causal scaling. No matched IO-path control is claimed.

Candidate checkpoint SHA256: `9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159`. Every stage used policy version `learned-update2-capacity-v1`, barrier inference, a 120-second limit, and zero optimizer steps. Native battle execution remains delegated to BattleAI and the economic policy remains scripted.

Evidence per stage: `plan.json`, `batch.json`, `INDEPENDENT_RAW_AUDIT.json`, `RESOURCE_AUDIT.json`, `POSTRUN_LOCK_AUDIT.json`; stages 8 and 12 include the next-stage resource prediction gate. The 24-env Linux original is retained; `scale-24/ARCHIVE_MANIFEST.json` records byte-identical archived collection and regular native evidence, original absolute paths and SHA256s. External Data/Mods asset symbolic links are recorded as metadata without copying their targets. The first archive attempt dereferenced those links before rejecting verification; its partial copy and error explanation remain in `failed-native-copy-01` and `ARCHIVE_ATTEMPT_01.json`. Recorded paths have not been rewritten.

The separate CPU paired development evaluation in `../native-paired-dev-clean-01` gave clean prior and trained candidate the same 5/8 result, with zero discordant win/loss pairs. That evaluation provides no evidence of improved win rate. Capacity success does not alter that conclusion.
