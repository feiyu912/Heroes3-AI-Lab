# Four-environment clean-prior smoke, waiting for acceptance

No pool, GPU, game or optimizer was started by this preparation. The collector CLI was called **without** `--execute`; its actual generated four jobs are in `preparation.json`. `LAUNCH_CONSTRAINTS.json` captures the complete intended invocation including barrier mode, which the collector's minimal prepare-only JSON does not currently record. Frozen core code was not edited.

The required next gate is the parent's complete 12-game acceptance on the latest explicit-server-readiness snapshot (05b or a superseding fresh run) plus an explicit pool-release message. Existing failed acceptance-04/05b records do not authorize launch. Even when acceptance completes, this file does not launch anything automatically: the parent schedules it and confirms that the accepted native snapshot still matches. The latest `NATIVE_CUDA_RECOVERY_PLAN.md` sets `--seconds 120` for smoke and recovery runs.

## What four environments means

Static source review confirms one loop iteration per job, each with a unique `env-NNN/agent`, worker process, native PID file and independently isolated native run directory. They share one supervisor-held pool lease FD and one manager model/GPU learner lease. Barrier mode waits for a request or terminal from each active environment before forwarding the batch. There is no optimizer in this CLI.

The actual four jobs use train-01-mines: EmptyAI in both roles, then Nullkiller2 in both roles, seeds 2026102200–2026102203. This smoke is **not** the trainer's full two-map balanced update. The trainer collects eight episodes across both maps before any update, using four waves at 2 environments or two waves at 4.

After the smoke, run the read-only resource audit:

```sh
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-v1/audit_collect_resources.py \
  --run /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-v1/native-collect-clean-4env-01 \
  --out /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-v1/NATIVE_CLEAN_4ENV_RESOURCE_AUDIT.json
```

Require four native PID files, a resource sample containing all four native PIDs and four worker session leaders simultaneously, four strict valid complete terminals, exact request consumption, no movement/economy/query rejections or unconfirmed terminal actions, zero optimizer steps and no leftover batch processes. A barrier batch can shrink as environments finish; a forward batch of four is desirable evidence but is not itself proof of four simultaneously running native processes.

## Measured source and prospective budget

`../NATIVE_COLLECT02_RESOURCE_AUDIT.json` independently recomputes the old two-environment run from its original JSONL rows and records their SHA256. That run used an **older learned checkpoint/native/async protocol**, so its outcomes are not copied to this clean-prior/barrier smoke. Its measured process peak was RSS 226,971,648 bytes, PSS 181,818,368 bytes; sampled Torch allocator peak was allocated 34,665,984 / reserved 35,651,584 bytes; swap was zero. It recorded both native PIDs and both worker sessions simultaneously, 46 resource samples, maximum forward batch2 and candidate width101. Wall time was 10.384 seconds for that old workload only.

A simple doubled workload with 25% margin projects about 0.57 GB worker/native RSS and 0.089 GB Torch reserved memory at four environments. These are planning estimates, **not upper bounds**. Manager CPU RSS, CUDA driver/context memory and transient allocation spikes are not included in those token-scoped/Torch fields. Changed economics, the clean prior, NK and barrier scheduling can change trajectories and latency substantially. The collector retains the actual RAM/swap/disk and failure gates, not this projection.

Allow an engineering budget of roughly 0.5–3 minutes for the first four-environment smoke, without treating that range as a measured ETA. Each worker has a 120-second native limit; the manager's 140-second elapsed limit plus cleanup bounds a problematic wave at roughly 2.5 minutes after setup. Any timeout remains invalid rather than a loss.

For the complete real training boundary comparison, each recipe executes four total updates: continuous2, split1, then resume to target2. At 2 environments this entails 16 waves total; at 4 environments, eight waves. The per-wave timeout/cleanup planning budget is roughly 40 versus 20 minutes if every wave reaches its bound, plus setup/PPO/checkpoint time; normal cases may be much shorter. The existing ten-second old run is not sufficient to promise new training throughput.

## Two versus four environment recovery recipes

Only begin after clean smoke acceptance and explicit parent scheduling. Use fresh output directories; default epochs4/minibatch64, seed base, source/native snapshot and barrier mode must remain identical within each continuous/split/resume comparison. For each `N` in `2` then `4`:

```sh
PY=/root/heroes3-ai-lab/gpu-venv/bin/python
TRAINER=/mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-v1/parallel_trainer.py
CLEAN=/mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v2/checkpoints/threat-supply-clean-prior-v3.pt
# Substitute a fixed N and explicit fresh output paths; these commands are not run here.
$PY $TRAINER --out CONTINUOUS_N --execute --environments N --updates 2 --seconds 120 --inference-schedule barrier --initialize-from $CLEAN
$PY $TRAINER --out SPLIT_N --execute --environments N --updates 1 --seconds 120 --inference-schedule barrier --initialize-from $CLEAN
$PY $TRAINER --out RESUME_N --execute --environments N --updates 2 --seconds 120 --inference-schedule barrier --resume SPLIT_N/update-1.pt
```

`--updates 2` on resume means target total2, not two additional updates. Run recipes serially with one GPU learner. A 2-environment checkpoint cannot masquerade as a same-protocol 4-environment resume; source/config/slot count changes require explicit initialization and a new recipe. Do not compare raw checkpoint byte hashes as the equality criterion because direct-parent lineage intentionally differs. Compare archived requests/actions/logp/value/terminal returns, actual parameter tensors, Adam state, CPU/CUDA/Python RNG and pure episode-generator state; separately report provenance. CPU04 fake barrier exactness does not establish native/CUDA exactness in advance.
