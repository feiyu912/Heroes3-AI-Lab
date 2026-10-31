# Actual local-battle retraining, 2026-10-20

B64 weights/new Adam, final graph layer plus policy/value heads, eight native workers balanced between attack/defense and BattleAI/original public MMAI CPU ONNX. Four real PPO updates,1024 sampled transitions,256 actual CUDA Adam steps.40 normal training endings,33 wins,0 truncations. Training performance is not independent evaluation. Four full checkpoints saved and read back model/Adam/RNG; no claim of restored live native battles.

Fixed64 DEV games paired the original B64 and final update4 on eight historically seen DEV maps, both roles/opponents, fresh fixed seeds. BattleAI15/16→15/16; public MMAI11/16→10/16.0 illegal/truncated/nonnormal results in all four arms. No improvement certified; candidate131e7c1c67805eaa1482e7d4680353af539c57e650ad5f78ff259a695673fd3e remains experimental and does not replace B64. Confirmation-v2 unused. Detailed per-pair independent analysis pending.

Original v1 launcher stopped before any native/CUDA update because bootstrap data was outside the required workers directory. Failed output preserved. v2 changes only that launcher path; no old source or evidence edited.

delivery-01/update-4.pt is a verified copy. delivery-01/raw-evidence.tar.gz covers completed training plus four complete raw evaluation folders,175 regular files; archive/source-before/source-after exact, no links followed. SHA8fb51221fcbf58b796a4d986214d1d909433ae1028dee4cd6ccaa1f4c50484d9. Linux originals retained.
