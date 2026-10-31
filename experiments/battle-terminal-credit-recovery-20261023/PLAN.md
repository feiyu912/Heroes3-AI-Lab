# Completed learner boundary recovery after resource stop

The original bounded run failed its update64 post-update memory/swap guard. Its
RESULT remains false. The exact failing live metric was not saved; update63 had
7142.63MiB available and181.57MiB swap. Do not invent a retrospective measurement.
Heavy CPU cross-arm diagnostics overlapped native learning; they may have
contributed, but causation is not established. This continuation serializes all
large CPU audit/analysis work between learner processes and records live memory.
Original resource limits, workers16, PPO, factor, native budgets and seeds remain.

Independent recovery review checked control63/64 full CPU model/ordered Adam/four
RNG and counters, all256 phase1 native journal records, raw reward/targets, suffix
zero loss and private RNG. Update64 is a complete phase-end learner boundary
(8192 actual Adam,2048 admitted plus2048 suffix cumulative), even though the
original run failed resources before normal stage reporting. That failure is not
reclassified as an engineering pass. Actual CUDA restore is checked at next use.

Resume control at65 from its verified64; resume candidate at63 from its completed
62. No reset, replay of control phase1, resampling, extra update, seed change,
qualification replay or interim DEV. Candidate phase1 has never run and runs once.
Then compare matched8192 and advance original phases2/3 to both8704/global68.
Each stage uses unchanged frozen original train.py and audit.py. All other
original source/native/environment inputs remain immutable. Fresh native phases
are already required by the original registration; no in-flight state is restored.

GPU then pool nonblocking locks and inherited real descriptors remain mandatory.
Large CPU replays must wait until learner and all workers stop. Lightweight memory
telemetry runs during learning without tensor loads. Any further gate failure
preserves the new result and stops, never scores a game loss or forces budgets.

Only if both exact-budget chains reach68 and all remaining raw/target audits pass,
run the originally registered96 DEV once (cases192..199,seed2026107600+index*100,
same public opponents, complete raw audit and full CPU proposal replay). No DEV
has begun. Describe any outcome as this explicitly recovered comparison with an
asymmetric earlier resource stop, not an uninterrupted original-protocol pass.
No automatic promotion, final-test access or strength guarantee.
