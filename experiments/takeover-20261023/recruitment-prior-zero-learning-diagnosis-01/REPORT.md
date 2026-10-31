# Prior-zero TRAIN same-observation learning diagnosis

Read-only replay of 3326 sealed observations from all 8 TRAIN cells. No DEV, native game, GPU use or optimizer step.

Initial recruit bias 0; updated -0.00778016727. See AGGREGATES.json for the same-observation op/argmax/margin and stock/bucket strata; EPISODES.json records actual recruited and transferred amounts separately from town/reinforce observations.

Frozen minus4 init, zero init and zero updated models are replayed on this single new TRAIN support. Minus4 to zero init measures manual-prior sensitivity; zero init to zero update measures model changes on the same states. Old 3952-state means and new state means cannot be directly subtracted as a pure model effect. No previous DEV evidence is read. Terminal advantages are episode-balanced and cannot prove that an individual earlier recruitment, town visit or economic decision caused the result. TRAIN successes are not independent strength evidence.
