# Frozen curriculum DEV paired result

Baseline74158291…:5/8. Candidate539850b6…:6/8. Eight fresh-seed paired cells,16 strict native games, one win/loss discordance. This is a **small positive development observation**, not a certified general strength gain, final-test result or win-rate guarantee. Both maps were historically seen DEV maps; neither is part of the new eight-cell training batch. Final test maps remain untouched. No evaluation sample or optimizer update was admitted.

| Pair | Map | Opponent | Director role | Baseline | Candidate |
|---|---|---|---|---|---|
|0|DEV river|EmptyAI|red|win|win|
|1|DEV river|EmptyAI|blue|win|win|
|2|DEV river|Nullkiller2|red|win|win|
|3|DEV river|Nullkiller2|blue|loss|loss|
|4|DEV reserves|EmptyAI|red|win|win|
|5|DEV reserves|EmptyAI|blue|win|win|
|6|DEV reserves|Nullkiller2|red|loss|loss|
|7|DEV reserves|Nullkiller2|blue|loss|win|

Both arms used the same ACK-drain native binary,41 runtime Lua files, CPU argmax broker, map/seed/role and same-length arm paths. Models stayed frozen. All5052 actual MoveHero/EndTurn applies and matching native consumption were checked (4570 policy moves,482 automatic EndTurns). Initial published requests matched exactly in all8 pairs.

`paired-choice-analysis-01/AUDIT.json` refines that initial-state check: pair3 later diverged in request17 **before** its first different strategy choice18. Native/opponent nondeterminism therefore remains and broad causal claims are unjustified, even with an identical executable. Keep the pair; do not discard it. Its outcome was loss/loss.

The unique flipped pair7 first chose differently on the **same request121/day14**, with all earlier requests agreeing; subsequent state/request divergence begins122. Baseline chose frontier[16,16,0] via[18,20,0]; candidate chose frontier[13,19,0] via[17,21,0], both equal heuristic score1.48004. Baseline lost day75; candidate won day122. This is consistent with a useful changed strategic path, but does not isolate every later event or establish robust superiority.

Further raw-history audit (`paired-world-prefix-audit-01`, `movement-order-audit-01`) qualifies that visible-request evidence: pair3's first differing server movement is already movement3 **before the first owned decision**; its pre-change movement sets differ. Pair7 also changes opponent hero ordering at movement38, after owned decision9, well before policy choice121; all320 recorded pre-choice movements have the same multiset within owned-decision boundaries, permitting an ordering-only explanation, but full hidden state/RNG equality remains unproven. Neither same initial request nor same visible request121 certifies identical whole-world histories. One preregistered same-baseline repeat (`typed-curriculum-paired-dev-03`, outside the eight-pair score) reproduces all357 published requests/choices exactly and the same loss, despite a different opponent movement order at movement36. No extra score or training sample is added. Root cause inside native/NK scheduling/RNG/tie-breaking is not yet isolated, and public opponent code is unchanged.

On all2103 baseline observations, both policies were independently replayed on CPU with the same singleton shape as evaluation. Baseline argmax reproduced exactly; candidate changed21 choices. Max centered logit change0.0572433, median0.0129452. Candidate best-move minus stop-logit gap stayed at least4.45825 (median7.56248). **Neither arm chose a policy EndTurn in any evaluation game.** The positive pair cannot be presented as learned waiting, retreat or human tactical understanding. Fixed heuristic priors and the committed-target candidate bottleneck remain concrete research limits.

The model really changed through164 CUDA Adam steps on8 mixed-terminal training games (4 wins/4 losses,2588 policy rows); its saved model, Adam including stop-bias moment and CPU/CUDA/Python RNG were independently recovered exactly in `checkpoint-cuda-audit-02`. This is separate from score and from continuous-vs-split native two-update equivalence, which is still unproven for this typed pipeline.

First evaluation attempt was aborted by the observer reading an unfinished JSONL line, before completing a pair. Its source/failed output remain. Attempt02 used the same preselected models/maps/seeds/endpoints, changed only committed-line observation, and passed91 split-write CPU cases. Original registration and amendment are preserved.

Authoritative raw result: `/root/heroes3-ai-lab/evaluations/typed-curriculum-paired-dev-02/RESULT.json`. This report never upgrades the accepted V8 environment or overwrites model9a6. Next work should address the measured decision/heuristic limitations and native nondeterminism before claiming broader learning gain; adding updates alone is not sufficient.
