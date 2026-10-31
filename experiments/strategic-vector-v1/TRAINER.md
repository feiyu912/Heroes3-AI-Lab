# Single-learner parallel strategic PPO

`parallel_trainer.py` is executable integration, not only a plan. One process owns the GPU learner lock before checkpoint loading, keeps the model fixed throughout all collection waves, invokes the separately reviewed episode-balanced PPO objective, then atomically saves a complete-update checkpoint. The source/binary/map/runtime configuration hashes freeze at **execution time**, so preparing this tool does not pin an obsolete native build.

No real GPU training was launched by this implementation branch. CPU fake-engine runs below performed actual finite-gradient Adam updates and real Torch checkpoint serialization. Native CPU throughput and parent-run GPU collection are separate evidence; neither is a learned-strength result.

## Schedule and recovery

Every update includes both training maps, both DirectorAI roles and both opponents (EmptyAI, Nullkiller2). With 2, 4 or 8 environments it collects the eight cells in 4, 2 or 1 waves. At 24 environments it collects three distinct seeds per cell, 24 full episodes in one wave. All waves use one fixed logical policy version `update-N` and one actual parameter digest. No optimizer step occurs until every episode in every wave passes the strict native/consumption/event gate.

The default inference schedule is `barrier`: each forward waits for one request or terminal from every active environment. `--inference-schedule async` remains an explicit throughput option with no bitwise reproducibility claim. Logical policy version determines the per-environment RNG stream; parameter SHA only records provenance. The earlier parameter-hash RNG design and its failed tests remain archived.

The PPO protocol excludes forced single-candidate rows from actor, entropy and KL objectives. Actor and critic weights balance complete episodes; the exact formulas and zero-choice boundary are in `episode_balanced_ppo.PROTOCOL`. A forced-only minibatch sets actor gradients to None so existing Adam momentum does not change actor parameters. Actual group optimizer steps and actor/critic deltas are reported.

Complete checkpoints contain model configuration/weights, Adam state and actual step count, CPU/CUDA/Python RNG, full recipe and SHA, every collection wave's environment-generator states, actual parameter digest, parent checkpoint SHA and complete lineage. The current saved checkpoint is passed to collection and its serialized parameter digest must equal the manager model. CPU recovery never restores CUDA RNG. Partial failure checkpoints preserve actual steps and weights but always set `complete_update_boundary=false`; resume rejects them. A changed source/runtime/configuration/slot count/algorithm recipe requires explicit weights-only initialization rather than a false same-protocol resume.

`--updates` is the target **total** completed update count, including resumed updates. The initial migrated default checkpoint retains its historical trained status. For a new strict experiment, the parent has selected the explicit clean prior; do not describe inherited legacy weights as untrained.

Prepare without loading a model or starting games/GPU:

```sh
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-v1/parallel_trainer.py --out NEW_DIRECTORY --environments 2 --updates 1
```

When the parent schedules real training after native acceptance, use the GPU Python, add `--execute`, and explicitly initialize the clean prior:

```sh
/root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-v1/parallel_trainer.py \
  --out NEW_REAL_DIRECTORY --execute --environments 2 --updates 1 \
  --initialize-from /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v2/checkpoints/threat-supply-clean-prior-v3.pt
```

Resume in a fresh directory with the **same recipe**, replacing initialization with `--resume COMPLETE_UPDATE_CHECKPOINT` and increasing target total updates. Scale changes require a new explicitly initialized recipe. Never run another GPU learner concurrently.

## Verification and limits

- `TRAINER_CPU_AUDIT_04.json`: actual CPU fake-engine barrier collection, eight balanced full episodes per update, continuous two updates versus one update saved/loaded then continued to two. Every request, action, old log probability, old value, terminal return, RNG seed and logical version is bitwise identical. Model, Adam, CPU/Python RNG and environment-generator states are bitwise identical after eight actual Adam steps. This is an end-to-end fake-engine test, not a replay-only test.
- `TRAINER_CPU_AUDIT_03.json`: actual async regeneration remains non-bitwise despite matching RNG states after removal of parameter-hash seeds. The failed result is retained; it explains why training defaults to barrier. Adam can amplify very small gradients arising from floating differences.
- `TRAINER_CPU_AUDIT_02.json` and the independent `strategic-vector-audits/cpu-boundary-drift-02/AUDIT.json`: earlier asynchronous value differences up to `5.96e-8` changed the policy digest, which then changed all next-update RNG seeds. This obsolete design's failure is preserved.
- `archived-boundary-cpu-01/AUDIT.json`: separately isolates actual atomic save/load with **identical archived** complete batches; model/Adam/RNG compare exactly. This test does not replace the CPU04 regenerated-game result.
- `trainer-failure-paths-cpu-03/AUDIT.json`: after a valid first wave, a deliberately injected second-wave native move failure prevents all update steps and saves a nonresumable partial. Partial resume and changed-environment recipe resume both reject before collecting new games. The private test harness injection is identified explicitly.
- `trainer-cpu-partial-04/training.json`: failure injected **after** one actual Adam step records step1 and saves `failed-partial-not-resumable.pt`, without pretending zero updates occurred.
- `native-gate-cpu-02/AUDIT.json`: normal/blocking visits and executed final missing-ACK cases pass; movement/economy/query failure and unexecuted terminal pending actions reject. A positive terminal military-visit proof is tested separately.

CPU fake barrier exactness does not prove bitwise CUDA/native-game recovery. Parent scheduling must still validate real CUDA collection, actual gradient updates, save/load boundaries and independent paired ability evaluation. Training wins and engineering throughput are not independent improvement evidence. Recovery is only at complete update boundaries, not arbitrary native action interruption.

Historical pilot02 terminal execution gaps are separately audited under `strategic-policy-v1/ppo-pilot-02/TERMINAL_EXECUTION_AUDIT_20261018/`; the original training.json, checkpoints, rewards and true optimizer history remain unchanged.
