# Recruitment TRAIN learning diagnosis

Read-only replay of 3952 sealed observations from all 8 TRAIN cells. No DEV, native game, GPU use or optimizer step.

Initial recruit bias -4; updated -3.99643612. See AGGREGATES.json for the same-observation op/argmax/margin and stock/bucket strata; EPISODES.json records actual recruited and transferred amounts separately from town/reinforce observations.

The zero-bias calculation changes only one logit offset on existing observations. It measures numerical sensitivity, not ability or the causal explanation of failures. Terminal advantages are episode-balanced and cannot prove that an individual earlier recruitment, town visit or economic decision caused the result. TRAIN successes are not independent strength evidence.
