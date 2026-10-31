# Paired development evaluation

All 16 games completed with strict native execution gates. Independent raw audit rechecked 5,949 requests/actions, persisted IO, native decisions and execution events; every frozen input matched. This was CPU argmax evaluation with no optimizer or GPU learning.

The clean prior and learned update-2 candidate each won 5/8 games: both won 4/4 against EmptyAI and 1/4 against Nullkiller2. There were zero discordant win/loss pairs and net paired win delta was zero. This evaluation supplies no evidence of improved win rate. Five paired action traces differed; different actions alone do not demonstrate improvement.

The eight pairs comprise two previously seen development maps, two opponents and two roles with preregistered new seeds. They are not eight independent maps and are not a final test. No independent-map confidence interval is claimed. Battle handling remains native BattleAI and the economy remains scripted.

Candidate SHA256: `9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159`.

Evidence: `plan.json`, `results.json`, `INDEPENDENT_RAW_AUDIT.json` and each job's persisted native logs/decisions/actions. The audit preserves per-model, role, opponent and map comparisons; validity certification is distinct from ability improvement.
