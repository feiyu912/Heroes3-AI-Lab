# Four-environment clean-prior CUDA collection

Completed after parent/tactics explicitly confirmed all 12 acceptance-06 games, independent raw gates and pool release. The accepted native snapshot was checked against the full acceptance protocol before launch (`prepared-clean-4env-01/ACCEPTANCE06_LAUNCH_CHECK.json`). No source or binary was changed during collection.

The clean prior SHA is `6ced669638242eff327c2b29c3ab635528f07167a7959a2170985f2dc304e2c9`. One central CUDA model served four independent native simulations using barrier inference and the shared inherited pool lease. A sample at 0.216771 seconds contains native PIDs 424–427 and worker session PIDs 420–423 simultaneously. Maximum forward batch size was four.

All four games completed with 717 byte-verified requests/responses and matching native candidate/action consumption. Independent raw re-audit passed (`INDEPENDENT_RAW_AUDIT.json`). There were 701 successful movement results and 16 legal blocking visits. One final ACK is missing **after its native movement result confirmed execution**; it is explicitly classified rather than treated as an unexecuted action. There are zero unconfirmed actions, rejected movement/economy/query events, changed policy/input hashes or leftover batch processes.

| Role / opponent | Decisions | Native day | Outcome |
|---|---:|---:|---|
| Red / EmptyAI | 242 | 25 | Win |
| Blue / EmptyAI | 191 | 23 | Win |
| Red / Nullkiller2 | 188 | 32 | Loss |
| Blue / Nullkiller2 | 96 | 11 | Loss |

These are engineering collection games on one training map with a fixed clean prior and stochastic action selection. They are not independent evaluation, learned improvement or gradient training. Actual optimizer steps: **zero**. Economics remain scripted and battles use native BattleAI.

Wall time was 11.8541 seconds. From 51 raw resource samples, worker/native peak RSS was 461,619,200 bytes and PSS 343,962,624 bytes. Sampled central Torch CUDA allocation/reservation peaked at 34,665,984 / 35,651,584 bytes; those allocator fields exclude CUDA driver/context and are not hardware-total VRAM or instantaneous kernel peaks. Swap remained zero, minimum system available memory was 14,473,846,784 bytes. Exact source-row hashes and concurrency witness are in `../NATIVE_CLEAN_4ENV_RESOURCE_AUDIT.json`.

The collection process exited zero. A separate nonblocking post-run probe found both GPU learner and simulator pool locks free, with no processes carrying this batch token (`POSTRUN_LOCK_AUDIT.json`). The parent may proceed to its separately scheduled fresh-process/restoration and real learning checks; this branch starts no learner.
