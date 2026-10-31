# Execution repair before game sampling

The original visible-exchange-v1 pilot exited before creating its first native
environment. The copied provenance helper required PLAN.md, while this candidate
registered its protocol as PREREGISTRATION.md. The raw failure log is preserved
in the original directory and copied to PREVIOUS_FAILURE.log for reference.
No win/loss, native game or training update came from that failed launch.

This new directory preserves the algorithm, thresholds, maps, roles and seeds.
It changes only the provenance document filename and new execution-directory
launcher path. run_pilot.py now exercises the actual map/runtime/source freeze
and verification path for both train cases before creating any worker or game.
The original directory, failure protocol and log remain unchanged.

Parent authorization permits this 16-game serial real pilot with the shared
simulation lock and no GPU learner. Existing development/test remain unrun.
