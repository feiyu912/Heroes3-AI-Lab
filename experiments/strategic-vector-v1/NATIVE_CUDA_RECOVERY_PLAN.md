# Native CUDA validation after explicit server readiness

This is a prospective engineering/training protocol, not a result. No final test
map is used. Original historical models and failed runs remain untouched.

1. Require full economy acceptance (four EmptyAI mechanism games and eight NK
   development games) on the explicit server readiness binary. A normal loss is
   allowed; timeout, rejection or unconfirmed action is not.
2. Run `collect_vector.py --execute --device cuda --environments 4
   --inference-schedule barrier --seconds 120 --checkpoint
   ../strategic-policy-v2/checkpoints/threat-supply-clean-prior-v3.pt` with a new
   absolute output directory. Require all four complete, every requested action
   confirmed, frozen inputs unchanged, no remaining processes, model unchanged,
   and zero optimizer steps. Inspect resource/batch logs for four real simulators
   and a single central GPU model before training.
3. Use `parallel_trainer.py --execute --environments 4 --seconds 120
   --inference-schedule barrier --initialize-from <clean-prior> --updates 2` for a
   continuous run. Independently run the identical protocol from clean prior to
   update 1, then load that checkpoint in a fresh process with `--resume <split
   update-1.pt> --updates 2`. Each update has eight complete games (two train maps,
   two opponents, both roles); the 32 physical validation games are only 16 unique
   policy/update game instances. They are recovery repeats, not 32 independent
   performance samples. No concurrent GPU learner is allowed.
4. Require the independent `compare_parallel_boundaries.py` default CUDA audit:
   exact request/action/old-logprob/value/return agreement, weights, Adam and all
   CPU/CUDA/Python/episode RNG, matching protocol/source/native execution evidence.
   Report any numerical discrepancy rather than silently relaxing to a tolerance.
   Each real Adam update, actor/critic deltas and checkpoint SHA must be reported.
5. Freeze the resulting candidate for `evaluate_dev.py`: clean-prior/candidate
   paired CPU argmax evaluation on two already-seen development maps, both roles
   and opponents, with new fixed seeds and alternate pair order. These 16 games
   (eight pairs, two map clusters) are independent of optimization but not an
   unseen-map final test. No improvement claim follows from training wins alone.
6. Only after actual four-environment resource/validity gates pass, advance to
   larger vector batches, up to the authorized 24. Changing environment count is
   a new protocol and requires explicit weights-only initialization, not a claim
   of strict same-protocol resume. Retain parent SHA and optimizer reset facts.

The clean prior SHA is
`6ced669638242eff327c2b29c3ab635528f07167a7959a2170985f2dc304e2c9`.
Scripted economics and native BattleAI remain declared. Failures abort before PPO
if no valid full batch exists; partial actual optimizer work is retained with
accurate step counts in a non-resumable failure checkpoint.
