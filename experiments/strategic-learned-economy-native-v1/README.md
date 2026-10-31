# Learned BuildStructure native candidate

Implements CONTRACT.md in a separate nine-payload candidate derived from the frozen capsule03 parent. No accepted source, previous capsule or schema4 Python interface was changed. New behavior requires `LAB_ADV_LEARNED_ECONOMY=build_v1`; unset retains schema4 and response-v1. New mode emits schema5 / response-v2 and epoch `learned-economy-build-v1`. It still uses one real hero and the original terminal +/-1 reward; no efficiency reward, transport or recovery work is included.

The first clean policy decision each own turn sees real native-ALLOWED ordinary build choices before optional economic spending. Build has a player/town actor, real town/building IDs and seven-resource cost; no fake path/coordinates. Build, Move and true EndTurn all close this one window. A selected BuildStructure enters the existing unique policy tuple and verifies actual sent player/request ID/town/building; it never sets pendingEconomy. Later recruitment/transfer/rescue remain scripts, and this mode has no scripted-building fallback. Movement commitments only update when selecting move. Actual buildChanged is observation only; the real PackageApplied callback closes the transaction. Old EndTurn tuple/query/battle/owned-terminal-drain barriers remain.

Observations:

- Original `DirectorTypedEvent` JSON/client mirror carries native_action_sent/build_changed/build_ack_state/package_applied with the immutable policy tuple, real town/building and before/after own-town/resources. Actual BuildStructure send payload is included under actual_request.
- Client `DirectorBuildPack` JSON/client mirror records actual SetResources (including its mode and signed values) and NewStructures (actual town/built counter/building set). Set `LAB_ADV_BUILD_PACKS=/absolute/raw/build-packs.jsonl`; default is `<LAB_ADV_AGENT_DIR>/build-packs.jsonl`. These are raw pack witnesses, not model observations; an auditor must filter/bind the own pending town/player.
- Server `TypedActionApplied ... op=build` plus `TypedBuildApplied player=... native_request_id=... town_id=... building_id=... success=...` records actual visitor result before ACK. Resource/building callbacks have no request ID: certify through the single pending transaction, exact cost/pre-post state, actual payload and matching native ID/ACK. Reject ambiguous/unexplained side effects.

Server effects precede server visitor result, but server/client log lines can interleave. Client effects precede the corresponding PackageApplied callback. build_ack_state/package_applied are printed inside that true callback, before the existing generic NativeRequestAck log; never treat the log-print order as a fake/missing callback. Automatic additional buildings must be justified by actual NewStructures, not silently dropped.

CPU checks:

```bash
python3 /mnt/g/Heroes3-AI-Lab/experiments/strategic-learned-economy-native-v1/check_cpu.py
python3 /mnt/g/Heroes3-AI-Lab/experiments/strategic-learned-economy-native-v1/check_native_syntax.py
```

Pure wire/window tests and source invariants do not prove native legality, callback ordering or execution. The syntax checker uses a temporary source overlay and `-fsyntax-only` for Director/server/client; it does not write shared source/object/binaries or link a native capsule.

Plan-only build entry (safe default):

```bash
python3 /mnt/g/Heroes3-AI-Lab/experiments/strategic-learned-economy-native-v1/build_capsule.py --out <fresh-plan-directory>
```

Root alone can add `--execute` under the shared resource locks for compilation/exact accepted restoration. The driver verifies the original accepted V8 full source manifest and three binary SHAs, not the parent candidate as the accepted tree. The only permitted removal is the added `AI/DirectorAI/TypedPolicyProtocol.h`; no generic deletion permission was added. Native mechanism qualification needs a new schema5 raw auditor/collector bound to this manifest; the old schema4 auditor remains strict. Root owns both those entry points and all native/GPU execution.

Shortest next path: isolated candidate CPU freeze → root build and exact restoration → real native Build/Move/End transaction and complete-game qualification → eight complete same-parent Training cells → exact CUDA replay admission → original +/-1 PPO once → paired DEV. No trained economic capability is claimed by this source candidate alone.
