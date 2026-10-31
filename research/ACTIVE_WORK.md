# Initial research and training acceptance, 2026-10-14

All authorized initial experiments and reports are finished. No trainer is scheduled to continue. Production remains 12 CPU simulator environments with GPU model inference and updates.

Final evidence: GOAL_PROGRESS_AND_RESULTS.md, TRAINING_THROUGHPUT.md, research/GOAL_RESULTS.json and research/ppo-research-suite.json. Ten valid PPO experiments completed 98,304 samples each (983,040 total). The unseeded mixed-opponent experiment is preserved but excluded; its seeded replacement is included.

Selected policy: models/selected-v3/policy.pt, chosen by validation results, with 88 wins in 160 held-out BattleAI battles. research/selected-trained-model.json records the original checkpoint and matching evaluation reports. GPU resume, masks, GAE, truncation final observations, cached bootstrap equivalence and seeded random-opponent replay passed.

This acceptance covers initial battle research and training. Full game AI is not complete: raw per-stack state, endgame pursuit, active magic, siege, strategic map decisions and full 1vs7 remain future engineering and curriculum work. See UPDATED_ROADMAP.md and STATE_INTERFACE_AUDIT.md.
