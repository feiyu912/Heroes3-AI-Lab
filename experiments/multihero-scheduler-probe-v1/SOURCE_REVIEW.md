# Scheduler source review

## Accepted scheduler

`/root/heroes3-ai-lab/src/vcmi-adv/AI/DirectorAI/CDirectorAI.cpp`

`CDirectorAI::pickHero`:

- filters by owner;
- skips heroes in `blockedHeroes`;
- chooses the owned hero with the greatest `movementPointsRemaining()`;
- does **not** check `CGHeroInstance::isGarrisoned()`.

`CDirectorAI::findTarget`:

- builds current-turn path information;
- scores visible enemy heroes, enemy towns, mines, own-town reinforcements,
  resources/pickups, and fog frontier;
- returns the selected candidate;
- external policy is only entered when `LAB_ADV_AGENT_DIR` is set.

The accepted `getHeroesInfo()` path returns the player's hero list without
filtering garrisoned heroes:
`lib/callback/CPlayerSpecificInfoCallback.cpp` (`getHeroesInfo`) returns
`playerState->getHeroes()`. The separate `getHeroSerial` has an
`includeGarrisoned` flag, but `getHeroesInfo` does not.

Therefore the original `pickHero` can see a garrisoned owned hero. Whether it
would have nonzero movement is an engine-state question; a real control fixture
would need to establish that, not assume it.

## What this run established

The third owned hero was placed on the town tile in the map object coordinates,
but it loaded as an ordinary mobile hero. It was not `isGarrisoned()` merely by
sharing the town tile. The scheduler selected it and the native engine applied
its moves. That is a fixture-control failure, not evidence that the scheduler
handles a true garrison correctly.

The two intended mobile heroes did receive successful native move ACKs across
two own turns. That observation is preserved but does not qualify the scheduler
because the control gate failed.

## Next source-derived options

1. Add `!hero->isGarrisoned()` (and, if required by the engine state, the
   appropriate visiting-town condition) to `pickHero`, then build a new
   isolated candidate and test a genuinely garrisoned control.
2. Or construct a genuinely blocked control (impassable-pocket/terrain or a
   runtime garrison setup) without changing scheduler semantics, and rerun the
   same gate.

These are separate single-factor experiments. Do not silently change the gate
or reuse the failed control fixture as if it had passed.
