# Strategic learning mainline, 2026-10-20

Resume the actual goal after user explicitly challenged the engineering diversion. Supply-v4 remains unfinished and shelved. No new native C++ or tactical expert course is part of this experiment.

Measured issue to investigate: previously fixed prior_scale=64 and stop_bias~-4, plus committed move pruning. Candidate poverty and probability saturation are separate. Audit only the previously certified eight TRAIN episodes; DEV labels are not optimization data. Preserve historical weights/source/evidence.

Single-factor candidate: soften the complete policy logits by temperature T in [1,2,4,8]. This scales the actor's final linear layer, stop bias and fixed prior together. It preserves argmax on every identical observation; it changes stochastic exploration, not the native legal candidate set or reward. Before seeing measurements, choose the smallest T>1 for which mean stop probability is >=1% and <=10%, subject to median move-conditional entropy on multiple-move rows >=0.15 nats and mean forward KL(parent||softened)<=0.5. If none qualifies, do not silently pick a temperature or train. This is an initialization intervention, zero gradient steps, explicit optimizer reset/new lineage. Do not claim learning from changed weights alone.

Then collect eight fresh TRAIN games, both train maps x both roles x EmptyAI/Nullkiller2, seed base2026102000, same derived parent. All complete strict native games plus exact CUDA sampling replay required before any update. One GPU model at a time, GPU then pool locks; no timeouts counted as defeat or partial curriculum updates. Existing terminal reward/episode-balanced PPO unchanged, one actual CUDA update with saved resumable state. If collection/admission fails, preserve it and diagnose instead of creating a score or retry loop.

Independent DEV comparison must use fixed fresh seeds and both arms on the same runtime, CPU argmax, no coordinate proxy. Training scores alone do not establish improvement. Since temperature preserves initial argmax, distinguish parent vs temperature-only and trained checkpoint; training must change decisions to explain any effect. Final-test data untouched.

Stop expanding infrastructure once this existing qualified runtime is connected. No multihero checkpoint implementation, replay viewer, expert relabeling, new battle scripts, or 24-env implementation in this step. Resource scaling follows a functioning learning loop.
