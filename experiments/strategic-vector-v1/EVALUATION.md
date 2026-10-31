# Paired CPU argmax development evaluation

`evaluate_dev.py` compares the explicit clean new-format prior against a frozen learned checkpoint using the current native mechanism. It creates no optimizer, calls v2 `smoke_game.py --mode new-policy`, and evaluates CPU argmax. The two fixed development maps have already been used historically. Neither final-test map is loaded.

Default seed base is `2026110300`, separated by map/opponent/role and seed index. One seed gives eight paired cells: two maps × EmptyAI/Nullkiller2 × red/blue. Each pair uses the identical native map/role/opponent/seed for baseline and candidate; first model alternates across pair indices. A pair is not an independent map. Summary records two **distinct** maps, assumes no statistical independence, and generates no confidence interval.

Preparation only, with no game launch:

```sh
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-v1/evaluate_dev.py \
  --out NEW_PREPARATION --candidate FROZEN_LEARNED_CHECKPOINT
```

Parent-scheduled actual evaluation uses a fresh directory and adds `--execute`. The default baseline is `strategic-policy-v2/checkpoints/threat-supply-clean-prior-v3.pt`; it may be overridden explicitly. Models, sources, native binaries/shared libraries, native/runtime configuration, Mods JSON and both dev maps freeze at invocation and are checked before/after every game. Candidate weights must remain unchanged; evaluation cannot silently read a newly replaced training checkpoint.

The native runner owns the shared simulation lock for each serial game. The evaluator separately tracks a unique inherited process token and cleans only its smoke/broker/runner/native descendants on failure or interruption. No GPU learner or global learner lock is required for CPU evaluation. It must still be parent-scheduled to avoid interfering with ongoing training's shared simulation usage.

Every request/action file, broker model identity, response hash and contiguous request ID is checked. Native selected index, full candidate array, player/day/hero/origin/target/step must match. The same strict native event/terminal execution gate used by collection rejects movement/economy/query failure and unconfirmed terminal actions, while accepting legitimate blocking visits and explicitly proven terminal military visits. An invalid result has `win=null`, not a fabricated loss. A failed or interrupted run writes atomic `status=failed`, retains evidence and certifies no aggregate scores.

Complete results report paired win difference, discordant pairs, map calendar days, and counts by role/opponent. They do not infer army attrition from before/after troops because scripted recruitment/reinforcement would confound such a measurement. They do not claim learned improvement from training wins or from a small development set.

`evaluation-cpu-forgery-02/AUDIT.json` is only a fabricated CPU fixture test: valid blocking visits pass; wrong checkpoint identity, action-byte changes, selected-index mismatch, candidate mismatch, missing v3 visibility fields, economy failure and unexecuted terminal pending actions reject. Its fabricated wins test summary accounting only and are not game results. `evaluation-prepared-01` is a preparation-only clean-prior self-comparison manifest, with zero games and zero optimizer steps. No real evaluation game was started by this implementation branch.
