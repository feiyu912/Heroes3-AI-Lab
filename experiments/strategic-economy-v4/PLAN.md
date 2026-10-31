# Dependency-complete military development — 2026-10-18

Problem verified from run-local Castle config and historical native traces:
dwellingLvl3 requires dwellingLvl4, while the Director priority list ends at 3.
The script therefore never requests 4 and cannot build 3; longer games continue
with only buildings30/31, even when resources are abundant.

Change only the isolated Director scripted builder: enumerate all seven base
dwellings and, when a dwelling is blocked by prerequisites, use the native town
dependency expression to select an affordable legal missing prerequisite. Keep
the existing economic order and native canBuildStructure legality check. No
map-specific building grants, income, army, battle rule or opponent change.
The economy remains scripted; do not report this as learned economics.

Gates before training on the new binary:

1. Preserve prior visible-v3 and query-only binary/source variants.
2. Reproduce the original query-chain failure seed with the query-only fix,
   then inspect native request ACKs; normal termination alone is insufficient.
3. New economy on both training maps and both roles against EmptyAI: verify
   real building33 prerequisite before32, recruitment of new unit types and
   army transfer conservation, no rejected economy/move requests.
4. Frozen train-map development vs Nullkiller2, both roles and two seeds,
   with native wins and losses reported separately from engineering acceptance.
5. Final-test maps remain untouched. Invalid games stop the batch and are not
   converted into wins/losses. This protocol does not certify model improvement.

Native turn-start save/load already passed under visible-v3 with224 request and
action bytes and complete state/decision/target trace SHA equal; rerun on the
final new binary as needed, preserving old evidence. This does not restore an
arbitrary mid-action or battle checkpoint.
