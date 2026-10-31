# Director targets v3 — 2026-10-18

This isolated native revision changes target execution, not battle rules.

* A target is retained within the current turn if it remains in the freshly
  generated admissible set. Each real move still has a broker request and native
  decision/ACK correspondence. A retained target has a singleton candidate set;
  its actor log probability is zero and it supplies no actor choice gradient.
  New turns, disappeared/reached goals and inadmissible paths release commitment.
* Combat kind 0 now includes visible neutral monsters, using only the native
  approximate quantity descriptor, with a conservative army-value filter.
  Hidden objects are not enumerated by policy code. This shares the existing
  combat feature with enemy heroes; this is an explicit semantic migration.
* Economics and battle control remain scripted/native BattleAI. These changes
  do not make the entire strategic policy learned.

Old pilot02 sources, weights and trajectories remain historical evidence. New
training must use --initialize-from for old weights and reset optimizer/update
count. Same-protocol resume applies only to newly produced complete boundaries.

Evidence: exact replay01 matches all 11823 original request hashes; replay02
adds visibility/path-node evidence; replay03 reproduces the same native decision
trace SHA and no-target tail. Monthly monster births before day1305 match the
old game. 11569/11803 remote choices change destination on the following step.
Fog-reveal accumulation showed no loss. The complete final frontier cutset has
not been reconstructed, so its exact neutral-monster causal attribution remains
open; missing neutral targets and excessive switching are independently verified.

Regression01 restores old update2 weights and saved CPU/CUDA/Python RNG under
the new native protocol, seed2026101930. It completed with a native victory in
237 decisions/day28, no optimizer steps. This is an engineering regression result,
not a paired independent ability improvement or evidence of new training.

Next gates: real CUDA training/save/load/boundary comparison, frozen paired
development evaluation, then environment throughput measurement. Final test
maps remain reserved. No win-rate claim is inferred from training curriculum.
