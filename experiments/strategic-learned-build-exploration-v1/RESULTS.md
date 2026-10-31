# CPU results and minimum next training integration

No native game, GPU sampling, optimizer step or expert labeling was performed. This is a preregistered initialization intervention using TRAIN only, not learning or an ability evaluation. Old policy/run/native sources remain unchanged.

The frozen3000 admitted TRAIN observations contain400 states offering1473 native build candidates:1291 infrastructure and182 dwelling. **There are no income-category candidates anywhere in this batch.** All19 actually sampled builds are16 infrastructure and3 dwelling. Therefore zero sampled income actions cannot be attributed to low income-choice probability; this dataset offers no income action to choose. The cause of native income-candidate absence is not established by this CPU audit. Adding build bias does not repair missing action coverage.

Parent is34a6… with188 historical CUDA Adam steps. `actor.build_bias` adds an independent trainable constant only to legal build logits. The inherited actor's existing build-op input can affect the nonlinear MLP, but changing its weights is not a generally exact constant-offset intervention. Adding one scalar preserves the feature43 interface and all other weights. Its derivative is exactly0 for a move logit,1 for a build logit; critic has no dependency. At zero offset, old/new logits and critic are bitwise equal on all3000 observations. No optimizer was stepped.

| Bias | Mean total build probability on400 eligible TRAIN states | Build argmax states | Mean KL(parent || offset), eligible |
|---:|---:|---:|---:|
|0 reference|3.649%|0|0|
|0.5|5.858%|5|0.00511|
|1|9.258%|20|0.02407|
|**1.5 chosen**|**14.299%**|**116**|**0.06394**|
|2|21.373%|259|0.13398|
|3|41.593%|379|0.40647|
|4|64.819%|396|0.90336|

Bias1.5 is the smallest registered candidate reaching10% without exceeding20%; no DEV data or argmax target was used to select it. The complete forward/reverse KL, probability/variation quantiles/extremes and high-probability counts are in `calibration-01/AUDIT.json`. Conditional distribution among nonbuild actions, including Move:EndTurn odds, remains exactly unchanged. Absolute move/end probabilities decrease as build mass increases; this is a real initialization behavior change. Critic remains identical. Income probability and income argmax remain0 because there are no income candidates.

New weights-only initialization: `calibration-01/build-offset-initialization.pt`, SHA256 `40eccc511fbc61b84b86e75b5aec102781835f2574db809f9a698f9a81db6d97`. Format `strategic-learned-build-exploration-initialization-v1`; architecture `schema5-build-logit-offset-v1`; new epoch `strategic-learned-build-exploration-v1`. This records a migration from the188-step parent but has0 new gradient steps and explicitly resets Adam/RNG/rollout. Existing loaders are not widened.

The shortest next training adaptation, if root proceeds after current DEV, is:

1. Derive new nested/isolated source-bound broker/model_io/admit/train adapters that import this architecture and strict initialization format. Keep current native schema5/capsule unchanged; action semantics and real-build audit still apply. A new resumable checkpoint format must explicitly bind architecture version plus `actor.build_bias` in Adam's named parameter groups and reject old-format resume. Do not mutate the frozen old12py.
2. Preserve the existing PPO function bodies/reward exactly. Because `actor.build_bias` is registered under `actor`, current actor grouping and forced-transition optimizer handling include it. New explicit Adam/RNG reset is required; historical188 steps are ancestry, not a continuous optimizer count.
3. Freeze one new source/protocol epoch and collect the complete eight fresh Training cells from the new initialization using the real CUDA multinomial sampler. Record real offered categories, build probability mass, selected counts and actual native application. Old3000 rows were only calibration data and **must not** be used as on-policy update rows for the changed policy.
4. Admit only complete raw-certified games with exact CUDA action/logprob/value/generator replay; perform an actual GPU PPO update and exact model/Adam/new-scalar-moment/RNG restoration audit. Then independently evaluate the updated policy under the same capsule and predeclared sampling rule. A higher build count or this CPU calibration alone is not success at economic strategy.

No transport recovery, new reward, new optimizer framework or native rebuild is required for this scalar intervention. The absence of income candidates is a separate coverage question requiring source/native eligibility evidence before any change.
