# Clean-prior native turn-start recovery: passed

Fresh CPU `new-policy` and native save/restore completed on map `takeover-v2-train-01-mines`, red DirectorAI versus EmptyAI, seed `2026102401`. Both finished with red victory on native day 13. This is a recovery and execution test, not an independent ability evaluation or evidence of learning improvement.

The checkpoint was `threat-supply-clean-prior-v3.pt`, SHA256 `6ced669638242eff327c2b29c3ab635528f07167a7959a2170985f2dc304e2c9`. Direct CPU loading confirmed `trained=false`, `training_updates=0`, `optimizer_steps_total=0`, and `optimizer=null`. The two games used CPU broker inference; no optimizer or GPU learning was run.

Each game emitted exactly 117 requests and 117 action replies. Re-reading raw native state traces and client logs through the frozen collector's native execution gate confirmed 117 native move replies and 117 `move_applied` acknowledgments, including 112 displacements and 5 blocking visits. Both had zero movement/economic/query failures, server rejections, missing execution replies, missing acknowledgments, or unconfirmed terminal actions. Each log contains two instances of the new server battle barrier ready marker. The terminal is the last of 567 state records in each game, so no tail notification exception or normalization was needed.

Every one of the 117 request files and 117 action files is byte-identical after recovery. The three whole trace files are also byte-identical:

| Raw trace | Records | SHA256, identical before/after recovery |
|---|---:|---|
| `strategy-trace.jsonl` | 567 | `67cc7cac9d123aab04d7e7bb0b30a4cc3910491f5caa851fddfacb605aa0d0be` |
| `strategy-decisions.jsonl` | 117 | `4958c3e7639f84002fb0446d8b63c1fa85c3bc14c2c05fa224047e0d748f1e0d` |
| `strategy-trace.jsonl.targets.jsonl` | 18 | `11690f85355eeba30d47a648e6de94ac7688f55c0c0ef941cc43cf67c1aaccbb` |

The original first-turn save was 341263 bytes, SHA256 `cab402d3f364c10b0d84867c7a9728b5175b98f05050f01194ddb8d771e4811f`. Recovery independently reports all three native load markers and `native_load_verified=true`; its staged snapshot has that same save SHA. Native full client logs differ, as expected for fresh startup versus load, and are retained without claiming byte equality for those logs.

`PREPARATION.json` verifies the fresh new-policy/model scope, original checkpoint identity, actual new-server barrier log marker, all three installed server source SHAs, save header and boundary, input freezes, and original action/candidate consistency. The independent `AUDIT.json` rechecks the union of preparation and restore frozen inputs after both games: no changed path. It preserves each request/action SHA and both complete native execution audits. No frozen core, native input, model, or binary was edited for this test.

The shared pool and GPU learner locks were both successfully probed with nonblocking exclusive acquisition after recovery, and the fresh/restored run tokens had no remaining process. The probe descriptors were closed before notifying the parent. Parent then began separate CUDA training; this report does not describe those later resources or results.

Raw original agent: `/root/heroes3-ai-lab/workers/strategy-agent-runs/cleanprior-turnstart-2026102401-_91neko_`.

Raw original native: `/root/heroes3-ai-lab/workers/adv-runs/cleanprior-turnstart-2026102401-2026102401-br5nqeqw`.

Raw restored agent: `/root/heroes3-ai-lab/workers/strategy-agent-runs/restore-v3-8qr4yqgl`.

Raw restored native: `/root/heroes3-ai-lab/workers/adv-runs/restore-run-2026102401-l0speh_n`.

Re-run only the read-only audit with `/root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-audits/cleanprior-turnstart-2026102401/audit.py`. This reads original artifacts and CPU-loads checkpoint metadata; it launches no game and acquires no pool/GPU lock. Original preparer and restore commands are preserved in `PREPARATION.json` and `restore-run/plan.json`.

Scope is first-own-turn native save recovery with no active battle. The transient server battle barrier state is not serialized. This test makes no claim about midbattle/query/action recovery, PPO optimizer/RNG recovery, CUDA reproducibility, or stronger strategic play.
