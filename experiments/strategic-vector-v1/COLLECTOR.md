# Synchronous central-policy vector collector

`collect_vector.py` collects full-game episodes with one model in one manager process. Native game workers use the independently measured inherited simulation-pool lease. Only the manager imports Torch and performs inference; workers do not start GPU learners. This module creates no optimizer and performs **zero gradient updates**.

The native CPU simulator throughput evidence is in `../cpu-simulator-throughput-v1/RESULTS.md` and `AUDIT.json`. It establishes simultaneous 24 native/worker pairs for that bounded heuristic workload. It does not by itself validate CUDA collection, parallel PPO, sustained training capacity, or policy quality.

## Python API

```python
rows, episodes = collect_parallel(
    model, jobs, out, device, policy_version,
    checkpoint=checkpoint_path,
    gpu_lock_fd=learner_lock.fileno(),
    gpu_lock_identity=(stat.st_dev, stat.st_ino),
    seconds=90, batch_wait_ms=2,
)
```

Each job supplies `map`, `red`, `blue`, `seed` and exactly one DirectorAI player. One job equals one environment/episode, up to 24. `out` must not already exist. Use a unique new directory for every batch. The caller owns the model on the requested device; CUDA API callers must already hold the exclusive GPU learner FD and pass its device/inode. The FD is validated before copying GPU weights for the policy digest. CLI mode acquires this lock before moving the checkpoint to CUDA. The collector closes only its duplicate references and never unlocks the caller's shared open description.

The simulation pool is acquired nonblockingly for the entire collection. Alternatively pass `pool_lock_fd` and `pool_lock_identity` for an already-held lease. All workers inherit the same locked open description, validate device/inode/exclusive ownership, and never unlock the global pool.

The model remains fixed in evaluation mode under `torch.no_grad()`. Each environment has its own `torch.Generator(device)` seeded from SHA256 of job seed, map, roles and the **logical policy-version label**. The actual parameter SHA is provenance and an immutability check, never a random-stream seed. `torch.multinomial` samples each **unpadded legal row** using that environment's generator. `inference_schedule='async'` forwards the ready microbatch; `barrier` waits until every active environment has one request or a terminal, then forwards all ready requests together. The trainer defaults to barrier; standalone collection defaults to async for throughput probes.

Every returned row includes `episode_id`, `episode_index`, full validated `request`, `action`, `old_logprob`, `old_value`, terminal `return`, request SHA, policy version, policy tensor SHA, checkpoint SHA and environment RNG seed. `episode_id` includes the job, environment index and policy identity, and is suitable for the new episode-balanced PPO objective.

The synchronous barrier requires **all** episodes to terminate natively, retain frozen inputs, and match every committed request against native candidate arrays, selected action index, player/day/hero/origin/destination/step and original request bytes. Any invalid episode, timeout, schema error, resource breach, input/model mutation or cleanup failure aborts the **whole** batch. `BatchAbort` exposes `episodes` and `accepted_rows=[]`; there is no `accepted-rollout.jsonl` for an invalid batch. Do not train from individual `committed.jsonl` files, which are quarantined evidence until whole-batch acceptance.

The strict native event gate additionally rejects `move_failed`, `economy_failed`, query-reply/server rejection logs and unconfirmed execution. Legal BLOCKING_VISIT result3 is accepted. A final missing ACK is separately recorded when the native movement result proves execution. If both final reply and ACK are missing, a military target requires causal native evidence: matching service-side hero request, same-hero visit and subsequent native battle/capture outcome before terminal. A post-battle request issued just before gameOver without that execution evidence is rejected, not silently trained. `native-gate-cpu-02/AUDIT.json` tests all these distinctions.

Only after the barrier returns successfully may a learner update. `parallel_trainer.py` now supplies the separate single-learner integration, documented in `TRAINER.md`. `collection-boundary.pt` stores final per-environment generator states and complete-collection identity; it is **not** a training checkpoint, optimizer checkpoint or a promise of arbitrary native game-state restoration.

## Evidence and scheduling

`CPU_VECTOR_AUDIT.json` preserves the earlier collector's CPU engineering test; current end-to-end boundary evidence is `TRAINER_CPU_AUDIT_04.json`. The earlier test shows:

- Two CPU fake runs use reversed ready delays and batch waits of 0 ms versus 10 ms. Actual batch sizes differ (maximum 2 versus 4), but each environment has identical action/request/seed sequences and identical final generator states.
- Replaying log probabilities on CPU gives zero difference; critic values differ at most `5.96e-8` between batched/singleton evaluation.
- Explicit per-environment sampling leaves the global Torch RNG unchanged.
- Injecting one native selected-action mismatch aborts the entire batch, accepts zero samples and produces no accepted rollout.
- All fake episodes validate native request consumption; model weights stay unchanged; no batch processes remain; optimizer steps are zero.

These tests use only private fake engines and CPU Torch. **No real CUDA/vector game was launched by this implementation branch.** The parent schedules real 2-environment collection first, reviews correctness/resources, then 4 and 24. Initial two-job CLI curriculum is engineering validation against EmptyAI in both roles, not a balanced capability evaluation. Larger default jobs include Nullkiller2 and the second training map; no dev/test maps are used.

CLI defaults to preparation only:

```sh
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-v1/collect_vector.py --out NEW_DIRECTORY
```

Explicitly scheduled real collection uses the GPU Python, `--execute --device cuda --environments 2`, and a fresh output directory. CPU fake collection uses `--execute --synthetic --environments 4`; this forces CPU mode regardless of the CLI device default. Do not run a second GPU learner alongside the manager.

Per-microbatch size, candidate widths, inference/sampling time, policy identity and device are logged. System RAM/swap/disk and token-scoped process RSS are checked approximately every 200 ms; CUDA manager allocated/reserved memory is recorded when applicable. Native/supervisor TERM/INT cleanup is inherited from the throughput protocol. Supervisor SIGKILL or children deliberately stripping their token still require external supervision and are not claimed covered.
