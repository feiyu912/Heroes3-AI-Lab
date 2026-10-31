# Owned-start-army x4 TRAIN curriculum: finite isolated follow-up

Registered factor: only the actual owned hero's starting army is multiplied by four on the private TRAIN map copy. Opponent armies, header, terrain, resources, towns, the zero-prior initialization, the eight map/role/opponent cells, the native seeds, the native capsule, terminal reward, Adam LR and episode-balanced PPO remain unchanged. The original maps and the shared runtime `Maps` directory are never written.

## Why x4

The completed TRAIN-only calibration (`strategic-active-opponent-calibration-20261023-01`) ran exactly twelve pre-registered Nullkiller2 games with the fixed zero initialization, CPU argmax, no optimizer and no admission. x1 was 0/4, x2 1/4, x4 2/4. The pre-registered rule selects the first boosted level in the order x2 then x4 with at least 2/4 normal-terminal wins, so x4 was selected. `SELECTION.json` records the calibration RESULT path and SHA, all twelve cells and the selection. This is a TRAIN difficulty selection, not an independent win-rate estimate, not DEV evidence and not an expert label. The calibration games are not training samples.

The four x4 variants are taken unchanged from the reviewed 12-variant `MAP_MANIFEST.json`. `MAP_DERIVATION.json` records each source and variant SHA, the exact two JSON amount edits, the original/modified armies, and the checks that every other object, header and terrain payload are unchanged. The manifest is re-validated before every cell and every source input is frozen by SHA.

## Training design

Exactly eight new TRAIN rollouts use the same cells and seeds as the prior-zero batch: `2026103900..2026103907`, with the same source-map/opponent/role order, the same sampling-generator seed derivation (the derivation deliberately uses the original source-map identity so the cells stay paired), and the same initial learner RNG seed. The actual private map variant is recorded separately in every episode plan. Reusing seeds does not reuse old samples or native in-flight state; trajectories may diverge because the starting army changed.

Each cell must be a complete normal native terminal with typed transactions, transport drain, full-state recruitment and free-transfer proof, exact CUDA sampling replay and unchanged inputs. Any timeout, invalid game or unfinished transport aborts the batch before an update; an invalid game is not a loss and is not silently replaced. Exactly one PPO update is allowed after all eight admissions, with the unchanged four epochs/minibatch 64/LR 3e-4 protocol. The update result is not an ability claim.

## Evaluation

Paired CPU-argmax DEV uses the two original DEV maps, both roles and both opponents, fresh seeds `2026104200..2026104207`. The four arms are the frozen minus4 initialization, its frozen update, the zero initialization and this x4-trained update. Eight cells and thirty-two unique native games share each cell's native seed. No DEV sample enters training; DEV is not converted into expert labels. Final-test remains untouched. Equal initial public requests do not establish hidden-world determinism after policy paths diverge.

The independent DEV audit must re-run the raw audits and CPU proposals, and report wins, losses, recruitment, builds and losses separately. Training wins, parameter movement or a positive DEV delta are not a general win-rate claim. No model promotion is implied by engineering success alone.

## Execution and preservation

`run_pipeline_x4.py` is plan-only unless `--execute` is passed. It acquires `.gpu-learner-lock` then `.pool-lock` per cell through the existing collector, starts the broker before native, and keeps one GPU learner. The frozen battle build, accepted strategic sources/binaries, historical evidence and old models are not modified. This package adds only an isolated experiment directory and new evaluation outputs.
