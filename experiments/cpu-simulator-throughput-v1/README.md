# CPU simulator throughput protocol v1

Prepared tooling only: **no real game throughput run has been started by this branch**. This measures native CPU simulations with the scripted DirectorAI heuristic and native battles. It does not implement parallel PPO, use a GPU learner, or establish policy strength.

`worker_runner.py` is an isolated copy of the current adventure runner. Its original snapshot SHA256 is `b786989e0a91b910ecd0fd0138136f77fbf83187ca2f8a4dde58472050246846`. The training runner, native source, binaries, historical evidence and frozen battle environment were not modified.

## Schedule after strategic boundary and independent evaluation

Default invocation only writes a frozen protocol and launches no workers:

```sh
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/cpu-simulator-throughput-v1/measure.py \
  --out /mnt/g/Heroes3-AI-Lab/experiments/cpu-simulator-throughput-v1/NEW-PREPARATION
```

When the parent explicitly schedules a real measurement, add `--execute`. Start with `--stages 1,2`, inspect the evidence, then extend the prefix of `1,2,4,8,12,24` in a new output directory. The default full ladder advances only while all gates pass; reaching 24 real environments is not presumed.

Each scale runs four games per slot by default, balanced across both old training maps and both DirectorAI/Nullkiller2 roles. The same four fixed seeds repeat across slots for comparable CPU workloads. This intentional duplication measures throughput, not independent games or win rate. No development/test maps are touched. `--repeats` for real runs must be a multiple of four. Startup, output, integrity checks and cleanup are included in wall throughput; there is no warm-start throughput claim.

## Pool ownership and cleanup

The supervisor nonblockingly takes the existing `.pool-lock`; if held by another batch, it reports `blocked_pool_lock` without launching games. It retains the lock throughout the whole ladder. Workers receive the same already-locked open file description through `pass_fds`, verify device/inode against the global path, independently prove the path is already locked, and verify that the inherited FD owns the lock. Workers never call `LOCK_UN`. They close only their inherited references on exit.

Every worker/native/helper receives an unpredictable batch token. Normal native exit, timeout and supervisor TERM/INT clean worker sessions and native sessions before the supervisor releases its lock. Cleanup is scoped to processes that actually carry that batch token, not all Python/native processes. A missing result, invalid native terminal, source/binary change, timeout, failed worker or stale batch process stops escalation. Diagnostic/incomplete episodes do not become wins or losses.

SIGKILL of the supervisor itself cannot execute Python cleanup. Workers still hold inherited lock references while they live, but simultaneous supervisor/worker SIGKILL requires external cleanup supervision. Token-based cleanup also cannot promise to capture a child that deliberately strips its environment or escapes the host. These failure modes are not claimed solved.

## Resource gates

Sampled every ~200 ms, with per-process RSS, PSS where available, CPU ticks, thread counts, system load, available RAM, swap and disk space. RSS double-counts shared pages and is deliberately conservative; PSS is reported separately. Sampled peaks may miss short spikes, so the ladder is a pilot rather than a capacity guarantee.

- Before launching a stage and throughout it: available RAM must remain at least `max(2 GiB, 20% total RAM)`.
- Additional swap use over the run baseline must stay at or below 256 MiB.
- WSL native-log volume must retain at least 5 GiB free.
- Sum of batch RSS must stay at or below 70% of total RAM.
- Before scaling: previous peak RSS per slot × next scale × 1.25 must fit within current available RAM after reserving the RAM minimum.
- Every game must be valid, all batch processes gone and all frozen input hashes unchanged before advancing.
- A throughput drop greater than 20% versus the previous scale stops escalation for repeat measurement/diagnosis.

There is no artificial loss assigned for a resource gate; the entire measurement reports the gate and stops. Review real RSS/PSS, swap, load, latency and throughput before deciding whether 8, 12 or 24 is useful. A higher concurrency number alone is not success.

## Verification evidence

All tests below use private `/tmp` fake labs, sleeping Python fake engines and deliberate TERM-ignoring helper children. They do not acquire the real simulation pool lock, run VCMI or use the GPU.

- `synthetic-24-01/result.json`: all six scales 1/2/4/8/12/24 completed, 51 fake jobs total, no token-bearing processes left. At fake scale24 sampled RSS ~1.28 GiB and PSS ~0.57 GiB; these numbers describe the fake fixture and **do not predict VCMI capacity**. This run predates the additional rejection of an unlocked inherited FD; that stricter check was separately verified afterward.
- `synthetic-success-02/result.json`: 1/2/4 pass after CPU/thread/load measurements were added.
- `synthetic-failure-01/result.json`: injected fake-engine exit7 stops at scale1, does not advance to scale2.
- `synthetic-supervisor-02/result.json`: supervisor TERM cleans all children, competitor lock probe fails while active and succeeds afterward; wrong-inode FD and correct-inode-but-unlocked FD both reject before native launch.
- `prepared-protocol-02/protocol.json`: final prepare-only manifest and current source/binary/map hashes; no games launched. An execution creates its own new manifest rather than silently reusing an old preparation.

Reproduce synthetic supervision checks with `verify_supervisor.py NEW_OUTPUT_DIR`, or use `measure.py --execute --synthetic --repeats 1 --out NEW_OUTPUT_DIR` for the fake full ladder. Keep synthetic and actual reports separate.
