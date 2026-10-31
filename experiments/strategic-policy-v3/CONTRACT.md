# Typed single-hero CPU prototype

This directory prepares a learning interface. It has no native bridge, collector or trainer and does not prove that EndTurn is legally executed in a game. Frozen schema3 native/collector/trainer/model code is unchanged. The proposed protocol must pass separate real-native consumption and ACK tests before training.

`schema=strategy-candidates-v4`, encoder `strategy-typed-single-hero-encoder-v3`, model format `strategic-typed-single-hero-prior-v4` are explicit incompatible versions. Existing observation fields remain required, including visible_threats and own_towns. `own_hero_count` must be integer 1, excluding bool. `own_turn` must be a positive integer sequence number for this player's turns, excluding bool. It is observation identity, not an encoded feature. Future action delivery/ACK must bind request_id, player and own_turn; this CPU prototype does not implement that execution gate.

Candidates are explicit objects:

```json
{"op":"move","kind":5,"position":[10,8,0],"next":[9,8,0],"path_cost":100,"heuristic_score":2}
{"op":"end_turn"}
```

Move payload retains schema3 validation. EndTurn's exact key set is `{op}`; it has no kind, position, next, cost or heuristic. At most one EndTurn is allowed. Candidate lists must be nonempty; move-only, stop-only and mixed lists are supported. There is no retreat kind. Multiple heroes are rejected throughout this pilot rather than silently ending another hero's opportunity.

The 27-state vector preserves the 26-state prefix, then appends raw own_hero_count (always 1 for this pilot). State prefix index 9 is total legal candidate count/64, including EndTurn when present. Each 25-candidate vector preserves the 23 move features and appends `[is_move,is_end_turn]`. EndTurn has 23 zeros and bits `[0,1]`; it is encoded directly without inventing a position or projecting a dummy move. Stop-only observations can compute state with an empty internal move projection; the public typed candidate list still cannot be empty.

Actor and critic use the expanded 52-column joined input. Move logit = learned actor residual + old heuristic prior. EndTurn logit = learned actor residual + `actor.stop_bias`; it receives no move heuristic prior. The independent trainable bias starts at -4 as an engineering prior, which is not learned hold ability. Every stop-bias parameter is under the actor name prefix for future optimizer classification. Critic pooling includes the actual typed legal candidates, so mixed/stop changes both policy normalization and pooled value.

`migrate_weights.py` accepts only parent SHA `9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159`, reading bytes once for digest and tensor loading. For actor/critic first layers, old state columns 0:26 map to new 0:26, old candidate columns 26:49 map to new 27:50; ownhero/op-bit columns start at zero. Other old tensors copy unchanged; the new actor stop bias starts at -4. Move-only logits/value are mathematically equivalent at initialization. Floating-point equivalence is measured separately; it is not promised for arbitrary devices/batch shapes. Mixed/stop observations are explicitly outside this equivalence claim.

New checkpoints have an exact weights-only key set, no optimizer/rollout/RNG state, `resume_supported=false`, zero schema4 optimizer steps, parent SHA/history and explicit reset_optimizer/reset_rng/discard_rollout flags. The new loader rejects schema3 checkpoints and optimizer/rollout resume. Migration retains historical trained weights as parent provenance; it does not turn old updates into schema4 learning. Saving uses a temporary file, file fsync, atomic replacement and parent-directory fsync. Every new source uses local file loading without assigning `sys.modules['encoder']`.

Reproduce CPU verification with the CPU venv and `cpu_audit.py --parent <registered update-2.pt> --requests <schema3 request directory> --out <new directory>`. The audit checks actual real-parent prefix/logit/value error, stop-only behavior, operation/state gradients, separate bias, exact save/load, module isolation and invalid inputs. It starts no native process and performs zero optimizer steps. Failed audit directories are retained; use a new output directory for each run.
