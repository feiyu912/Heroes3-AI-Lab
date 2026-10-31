# Read-only review of the first build-offset TRAIN update

The eight complete admitted Training games contain1891 policy decisions and28 actually executed policy builds. All2425 distinct saved source, raw log, map/script/config and compiled-runtime inputs referenced by the original protocol/collection/raw audits were hashed and matched before and after this CPU audit. No new game, CUDA sampler or optimizer step was run. Complete per-input hashes are in FROZEN_INPUT_RECHECK.json; per-state and per-build data are retained alongside AUDIT.json.

Initialization SHA40eccc… starts at build_bias1.5 with fresh Adam/RNG/rollout. Trained checkpoint SHAd27d282b… has120 actual CUDA Adam steps, build_bias1.49731266499. Its ancestor34a6… had188 steps in a previous optimizer epoch. **These are not308 continuous optimizer steps.**

| Measurement on the same1891 collected TRAIN states | Initial | Updated |
|---|---:|---:|
|Mean total P(build),244 states offering builds|15.676%|17.168%|
|States where build is argmax|65|68|
|Mean probability of the28 actually sampled build candidates|4.533%|4.958%|

Forty argmax decisions change:25 move→move,6 build→move,9 move→build. Mean total variation is .016153; mean forward KL is .001394. The scalar bias decreases slightly while total build probability rises, so the shared actor's changes matter; probability changes cannot be attributed to the scalar alone. Critic and movement also change.

All28 actual builds are20 infrastructure,7 dwelling and1 income. Native legal build candidate occurrences are706 infrastructure,225 dwelling and2 income, offered across244 states. The two income opportunities are cell03 decision126 and cell05 decision160. The actual income build is cell05/day23/decision160, town19/building12,5000gold, real native request217. Its original GPU sampling probability was .040522465; the updated CPU policy gives .045600872 on that saved state. Both old/new argmax select another action there.

The earlier3000-state batch genuinely contained zero income candidates; this new batch contains two. Thus the earlier absence is dataset-specific, not evidence of a globally missing income operation. Different seeds and changed trajectories prevent interpreting the two batches' build counts as a controlled estimate of economic improvement.

Training outcomes are4 EmptyAI wins and4 Nullkiller2 losses. These are training results. This same-state CPU comparison is neither an independent paired evaluation nor evidence of improved overall strategy; root's separately frozen DEV experiment is required for that question.
