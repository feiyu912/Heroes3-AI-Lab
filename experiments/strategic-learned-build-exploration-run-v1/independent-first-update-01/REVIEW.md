# Independent exploration first-update review — passed

Actually reran frozen new-epoch raw audit for all 8 TRAIN + 16 DEV games; every report equals its original. Verified manifest/capsule/compiled source/raw/source hashes, 5381 actual policy bindings, and every real build cost/subject/server application/NewStructures/ACK. Actually recomputed all 3490 DEV full proposals/value/CPU argmax outputs using exact initial40eccc and trainedd27d models; all match. Original frozen files unchanged, no new native/GPU/optimizer run.

TRAIN: 1891 certified rows, 28 real builds including one City Hall, native wins/losses4/4, 114 real policy EndTurn. City Hall is cell05/day23/decision160/native request217/town19/building12, actual cost5000gold and exact state/application/ACK proof (CITY_HALL_EVIDENCE.json).

DEV: initial4/8 → trained4/8. Initial87builds/12income; trained47builds/3income. Neither arm chooses policy EndTurn. Counts differ with trajectory length; fewer builds alone is not a strategy-quality score.

| Pair / opponent / role | Outcome A→B | Native terminal day A→B | Builds A→B | Income builds A→B |
| --- | --- | --- | --- | --- |
| 00 / EmptyAI / 0 | win→win | 48→12 | 30→5 | 6→0 |
| 01 / EmptyAI / 1 | win→win | 14→14 | 8→8 | 0→0 |
| 02 / Nullkiller2 / 0 | loss→loss | 12→12 | 1→1 | 0→0 |
| 03 / Nullkiller2 / 1 | loss→loss | 32→54 | 9→12 | 0→2 |
| 04 / EmptyAI / 0 | win→win | 44→17 | 23→8 | 6→0 |
| 05 / EmptyAI / 1 | win→win | 24→25 | 9→10 | 0→1 |
| 06 / Nullkiller2 / 0 | loss→loss | 34→11 | 5→1 | 0→0 |
| 07 / Nullkiller2 / 1 | loss→loss | 15→15 | 2→2 | 0→0 |

Terminal calendar is reconstructed from the audited client.log server Turn/Info(n.day), received/applied NewTurn sequence and own typed game_over, with own_turn recorded separately. Faster losses are not improvement. Published initial request semantics match in 8/8 pairs; REPORT.json records equal-request prefixes, first differing actions and observations. This is not full hidden-state or RNG equivalence.

Calibration/causality: the initial model already has build_bias1.5 from a zero-gradient TRAIN-only initialization; CPU readback confirms the post-update bias1.4973126649856567. Both arms building does not establish that gradient learning created building behavior. The saved update is real, but this small DEV result shows no win-rate gain; day differences remain trajectory evidence with pairing limits.

Certificate-only checks: TRAIN CUDA action/logprob/value/RNG admission replay and GPU120-step exact model/Adam/RNG recovery with six invalid resume cases were not rerun here. Their certificates, immutable input/output/model/source chains and build-bias Adam assertion were checked. Calibration source/input hashes and zero-gradient initialization certificate were also checked, not re-executed.

Scope: only the completed first-update TRAIN/DEV directories were read. The separately frozen continuation controller is not asserted to be part of this checkpoint source protocol; no live logical1..3/continuation run was audited. Root raw auditor was reused; additional actual-action/cost/all-CPU-policy/calendar/result-label checks are independent here.

Artifacts: REPORT.json, AGGREGATE_AUDIT.json, BUILD_TRANSACTIONS.json, CITY_HALL_EVIDENCE.json, raw-reaudit/ and INPUTS.json. All original input hashes remained unchanged at final check.
