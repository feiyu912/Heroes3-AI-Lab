# Typed broker and native execution contract (prototype v1)

No native execution is certified by CPU fixtures. This interface adds EndTurn to baseline-V8 candidates; it does not inherit threat-release-A behavior. Native/schema3 plain-integer responses are incompatible and must not be accepted as fallback.

Observation is the existing strict schema4 request. `request_id` is the policy decision sequence; `own_turn` is a strictly positive integer own-turn sequence, not bool. The current pilot requires integer own_hero_count=1. Candidates are typed move payloads or exactly `{"op":"end_turn"}`. Requests must be generated only when Query, movement, economy and battle work is drained. Neither broker nor native may synthesize fake movement coordinates for EndTurn.

Response is one UTF-8 JSON object with trailing newline, written atomically to `action-NNNNNNNN.json`:

```json
{"schema":"strategy-typed-action-response-v1","selected_index":2,"decision_id":17,"player":0,"hero":44,"own_turn":3,"op":"end_turn","request_sha256":"64-lowercase-hex-characters","classification":"diagnostic_only"}
```

The exact response key set is the nine keys above. All integer fields exclude bool; selected_index is in the supplied candidate range; decision_id equals request_id, context equals the immutable request, and op equals the selected candidate. request_sha256 is SHA256 of the exact published request file bytes. classification is `new_policy` or `diagnostic_only`; it is provenance, never an execution proof. Native must verify every field, preserve the original candidate/context, and reject mismatches rather than falling back to a heuristic or another candidate. A response is a proposal, so it contains no invented native_request_id.

Normal broker `--mode new-policy` requires the new typed model format and uses CPU argmax. `--mode diagnostic-only --diagnostic-action end_turn|alternate` deliberately selects the named operation (alternate: odd decision_id move, even decision_id EndTurn). Missing requested operations are errors. Diagnostic proposals are engineering only and ineligible for PPO. No optimizer exists in this broker.

Two-stage binding is mandatory. At real requestSent, native emits `native_action_sent` with `decision_id`, the actual positive `native_request_id`, `player`, `hero`, original `own_turn`, `op`, `pack_type` (`MoveHero` or `EndTurn`), `selected_index`, original `request_sha256`, and exact selected `candidate`. The tuple stays immutable even if a later yourTurn arrives first. Policy consumption must match one proposal exactly and once. Real server/application and client/ACK events must repeat that immutable tuple (at least decision_id/native_request_id/player/hero/own_turn/op/pack_type); reusing the live current turn value in a late ACK is invalid.

Audit input is ordered JSONL native events:

* `your_turn`: player, own_turn (first=1; subsequent strictly +1).
* `busy_state`: player, own_turn, query_count (nonnegative int), movement_busy/economy_busy/battle_busy (strict bool). Each new turn needs a snapshot before an action. EndTurn requires all clear, and no unresolved same-turn action. An ended own_turn cannot send more actions.
* `native_action_sent`: immutable binding and full consumption fields above.
* `server_action_applied`: binding, source=`server`, success=true. For EndTurn this must be emitted from the actual service-side successful apply of EndTurn, not client request submission or a new turn.
* `package_applied`: binding, source=`client`, success=true, package=`PackageApplied`. Must come from the actual PackageApplied callback for precisely the matching request and pack type. Duplicate, failed, wrong-op or context-mismatched ACK is invalid.
* `move_result`: binding, source=`server`, result (native positive integer; zero is failure). Result3 BLOCKING_VISIT is legal and need not imply a displacement.
* Terminal military fallback, only for the final MoveHero: `server_move_received`, then `hero_visit`, then `battle_or_capture_outcome`, each server-sourced and binding-matched, followed by `game_over` (completed=true). Candidate must be military kind0/1 and next==position. This is real visit/battle/capture evidence, never winner alone. A final actual move_result with missing ACK can also be classified separately after game_over, matching the old move execution rule.
* `move_failed`, `economy_failed`, `query_failed`, `server_rejected` invalidate the whole run. Unknown events do not certify action execution.

EndTurn always requires both the service-side success and exact successful PackageApplied ACK. Winner, local skip, turn-end callback, next yourTurn and auto-end are insufficient substitutes. A late ACK after new yourTurn is allowed only with the old saved tuple; it must not clear or overwrite the new turn's pending action/busy state. Audit keys pending work by request ID and saved own_turn, never by current turn alone.

Automatic native EndTurn without a policy choice emits native_action_sent with decision_id=null, selected_index=null, request_sha256=null, candidate={op:end_turn}, `automatic_reason` (nonempty), and the real remaining binding fields. It gets the same apply+ACK requirements but a separate automatic count and zero policy samples. Policy EndTurn must never be reclassified as automatic to hide failed consumption. Unexpected or unconsumed policy decisions and any unresolved action invalidate the run; invalid win/reward remain null.

These JSONL events are a required instrumentation contract, not a claim that existing native code already emits them. The new audit rejects missing instrumentation. Native raw log evidence must be retained alongside the trace so event extraction itself can be independently checked before any real learning run.
