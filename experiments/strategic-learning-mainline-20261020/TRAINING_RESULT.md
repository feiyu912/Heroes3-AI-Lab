# Actual strategic training result, 2026-10-20

One complete on-policy eight-cell curriculum update was performed on CUDA. This is actual learning work, separate from the zero-step temperature initialization and native engineering success. No accepted/frozen environment or historical model was replaced.

| Evidence | Actual result |
|---|---|
| Failed first batch |6 admitted games, seventh raw audit rejected opposing NK garrison request, eighth not run;0 updates |
| Full second batch |8 strict native games, exact CUDA sampling replay;2742 policy rows |
| Training outcomes |4 EmptyAI wins,4 Nullkiller2 losses; training data, not independent strength |
| Actual CUDA work |1 PPO update,172 Adam steps for actor and critic; no early KL stop |
| Scripted/automatic actions |Excluded from policy samples; no script demonstration/BC/expert labels |
| Exploration behavior |173 sampled policy EndTurns;2123 one-move rows,619 multiple-move rows |
| Same-state learned changes |13/2742 argmax changes, all among multiple move candidates;0 initial/trained argmax EndTurns |
| Exact distribution shift |mean KL(initial||trained)0.000513799, max0.002406704 on fresh training states |
| Parameter delta from initialization |actor L2 0.8309891, critic0.8946033; stop bias -1.99775457→-1.99187732 |
| Saved model |bb3417624bdb25023e1dbbb2e8eb49de140f2a4264c9de0444659f2b953803cc |
| Actual recovery |model/Adam/stop moment and CPU/CUDA/Python RNG exact;5 invalid resumes rejected without mutation |

The old research checkpoint5398 had164 historical CUDA steps; this branch deliberately reset Adam after the T2 weights-only intervention. Do not describe164+172 as one continuous optimizer. The initialization preserves parent argmax; it is not a learned policy improvement. The increased sampling of EndTurn does not establish useful waiting: training still lost all four NK cells and the trained deterministic policy still chose no EndTurns on these fresh states.

Current native runtime remains single-neural-hero, scripted economic operations, native BattleAI combat. This experiment does not teach recruitment, multihero supply, human tactics or battle-level MMAI superiority. It tests a specific exploration limitation while preserving candidate generation and reward. Sparse terminal credit and missing destination choices remain limits; additional updates without addressing measured failure would not constitute an adequate method change.

Artifact shipped locally: trained-cuda-01/update-1.pt, copy SHA verified. Actual complete-boundary audit is checkpoint-cuda-audit-01/AUDIT.json. Behavior analysis is learned-policy-comparison-01/AUDIT.json. Full original output: /root/heroes3-ai-lab/evaluations/strategic-mainline-temperature2-train-02. Both attempts must remain visible. The first batch cannot be rescored or spliced into the second.

Independent DEV is a separate fixed-seed comparison of T2 initialization and learned checkpoint, same qualified native runtime, CPU argmax, no threat proxy. Its result must be read from the final DEV evidence, not inferred from the table above. Final-test maps remain untouched.

Final independent DEV result:16 strict games,6/8 versus6/8, all8 pair outcomes unchanged,0policy EndTurns. No strength improvement. Pair03 won day46 versus201 after training, with412 versus2496policy moves; other winning pairs include faster and slower outcomes. Final independent raw/model review: independent-dev-final-01/REVIEW.md. It found a first target-selection difference on identicalrequest37, but does not claim complete hidden-world equality or single-choice attribution of all delay. bb341762 remains an experimental artifact and is not promoted. New work therefore changes a measured learning limitation rather than repeating the same PPO updates.
