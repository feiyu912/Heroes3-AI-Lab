# One-time independent live snapshot

Snapshot UTC2026-10-20T14:56:13.021591, bounded read window .141s. Launcher285 held both real kernel GPU/pool leases; NVIDIA reported only learner422. Sixteen direct spawned workers all mapped actual libvcmi and libmlclient in this same window. Native engines execute inside these worker processes/threads; no extra sixteen executable PIDs or24-worker claim.

Host MemAvailable6784.55MiB, owned tree PSS8829.50MiB, host swap1.012MiB (not zero), ownedSwap0; GPU2177/16303MiB and51°C. These are one window's observations, not minima/maxima or final scale stability.

Control initial restoration metadata was checked against approved dcaab parent; actual CUDA/model/Adam/allfourRNG exact flags and hookcounter3840 present. Latest complete saved boundary global32=stage2, cumulativeAdam4096=parent3840+new256, newrows1024. Checkpoint/rollout hashes and494 current frozen inputs passed CPU inspection. This does not certify final two-arm training or DEV improvement.

`compact_status.py` is an optional one-shot file view, with no loop, native or GPU operations. It reports stage/cumulative counts separately for each model. No additional resource scan is scheduled.
