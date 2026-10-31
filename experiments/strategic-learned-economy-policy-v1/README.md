# Learned economic build policy — isolated schema5

CPU implementation is complete. This is not native qualification, a trained economic policy, or an ability improvement. No native process, CUDA sampler, GPU learner, or optimizer step was run by this implementation task. Historical schema4 sources/models were not modified.

The immutable native contract is `../strategic-learned-economy-native-v1/CONTRACT.md`, SHA256 `e9c0f43ccc0ef5e880f969863bf14665e2c80210acaaa2c5f36bf05516e14af5`. Native source/build/run qualification and raw evidence auditing are root-owned. The new `../strategic-learned-economy-run-v1` collector/common/auditor is a separate dependency still being implemented by root; its integrity and native qualification cannot be inferred from our CPU tests.

## Implemented entry points

- `encoder.py`: schema5, exactly one hero, real player-town build identity, exact seven resources/costs, visible own-town facts, strict build/move/end union. Coordinates are absent for build. Arbitrary town/building/faction IDs bind identities and are not continuous features. State35/candidate43. Candidate op bits40..42; economic cost23..29, spend fractions30..36, category37..39. Resource order wood/mercury/ore/sulfur/crystal/gems/gold. Native ALLOWED legality still needs actual native proof.
- `model.py`: movement prior acts only on move; stop bias only on EndTurn. Strict three-way op and payload checks. No invented build prior or extra reward.
- `migrate.py`: only the frozen d5908330… T2 initialization is accepted. Map old state27/move23/op2 into new first layers, zero all added columns, copy deeper actor/critic and biases. Explicit reset Adam/RNG/rollout, zero gradient steps. State[9] counts nonbuild candidates; this is deliberate feature migration metadata, not a raw request change. Build-mask tests compare nonbuild logits and critic with float32 tolerance.
- `model_io.py`: distinct initialization and resumable PPO formats; old loaders remain unchanged. Training checkpoint binds schema5, economic epoch, native contract and complete update boundary; CPU test checkpoints are rejected as training parents. Existing Adam/model/RNG binding logic is retained.
- `broker.py`: strict response-v2, nine exact response fields and SHA of exact request bytes. CPU argmax and explicit diagnostic build/move/end; diagnostics do not become policy samples.
- `onpolicy_broker_v2.py`: CUDA multinomial sampler using the same inherited exclusive GPU then pool leases and deterministic generator interface. Logs actual build candidate count and probability mass. CLI matches the original sampler; not yet executed on CUDA.
- `admit_episode_v5.py`: imports root's new epoch validator/collector, requires full native game/build evidence and exact CUDA action/logprob/value/request/generator replay. Admits only actual policy transactions, including real builds. Scripted recruitment/transfers/auto-EndTurn remain excluded.
- `episode_balanced_ppo.py`: only encoder/schema metadata changed. All PPO function ASTs match the frozen original; reward is native terminal win+1/loss-1. No optimizer step was run by CPU checks.
- `train_update_v3.py`: full eight Training cells, matching parent/runtime/source/logical update, new explicit initialization then resumable checkpoints. Refuses a batch with zero certified real build samples before acquiring GPU/performing an update. Same Adam/PPO/reward. Source integrity includes root's full new collector/auditor dependency set.

## Verified CPU results

`cpu-02/AUDIT.json` checks all2588 genuine historical TRAIN movement requests projected into the new feature epoch, and explicitly synthetic appended build fixtures. Masked-build old logit/critic maximum error each2.3841858e-7; all old argmax unchanged.26 syntax/tensor rejection cases pass. Backward-only synthetic build gradients are nonzero (economy columns L1 .3441814; build-op column .1783672). No optimizer was stepped.

Initialization saved/read back at `cpu-01/build-initialization.pt` and independently regenerated at `cpu-02/build-initialization.pt` has the same SHA256 `0dbbc4735e217e39a55dcd2f398b945bcb9ea6490525c86645843a5f1ac313f6`. Parent d5908330038444107ed9ba00585fb068e453a5d1636856ba994d9aa3eb68df72. This is a weights-only initialization, not a learned-build checkpoint.

Synthetic build probability probe:878 prior TRAIN states with an appended hypothetical2500gold income building; missing new town/resource metadata were explicit fixtures. Minimum .0017409, median .1931744, maximum .4446428; none below .001. This rules out an obvious structural near-zero initialization in this limited fixture probe. It does not establish real candidate appearance rates, actual selection rates, or native legality. Real qualification must measure these before training.

`hooks-cpu-02/AUDIT.json` passes13 wire/codec rejection checks, atomic fault preservation, CPU-test-parent refusal, and objective backward with synthetic build input. PPO function ASTs are unchanged. CLI imports for admission/training succeeded against root's current new helper. This does not validate the root's native audit implementation.

Earlier cpu-01/hooks-cpu-01 reports are iterative CPU results; source hashes reflect their then-current implementation, not the final source freeze. No native/GPU inputs were running or edited. `SOURCE_FREEZE.json` and source-freeze-01 hold the final current source snapshot.

## Distance to first real build-containing GPU update

1. Root finishes new native source and creates/restores a source-bound capsule.
2. Root qualifies actual build selection → same-ID BuildStructure server application → actual resources/NewStructures → successful ACK, plus move-instead-of-build and no-legal-build paths. Complete-game/terminal gates remain required.
3. Root freezes collector/auditor and executes CUDA sampling for the eight Training cells from this initialization, with real build probabilities/counts recorded.
4. New admission must pass native evidence plus exact CUDA sampling replay. At least one real policy build is required across the complete batch.
5. Root invokes train_update_v3 for a real CUDA PPO update, then independent same-capsule paired evaluation. Neither successful CPU checks nor positive training outcomes establish an ability gain.

No further framework, transport recovery, reward change, or24-environment expansion is required by this policy implementation.
