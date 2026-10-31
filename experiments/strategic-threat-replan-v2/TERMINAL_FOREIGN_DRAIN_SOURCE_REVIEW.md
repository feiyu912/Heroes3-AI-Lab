# Terminal foreign-request wait: read-only diagnosis

This diagnoses the preserved invalid engineering timeout at `/root/heroes3-ai-lab/evaluations/typed-clearance-proxy-paired-02/pair-03/b/native`. No native source, verifier, runner, original JSON or raw log was modified. No native/GPU operation occurred. The original game remains invalid/unscored; this report does not retroactively replace its transport gate.

## Raw facts

The original `EXECUTION.json` has `stop_reason=engineering_timeout`, `client_exit=-15`, `game_completed=false`, `winner=null` and `transport_drained=false`. The client log SHA256 is `e852f45cefccc255f1c300c67462c152b050926dc88b8f342aa6534d9e23c702`.

- There are 867 client request-send records, 866 received PackageReceived records and 866 received PackageApplied records.
- Owned blue Director has 237 policy MoveHero requests, 27 automatic EndTurn requests, 264 exact typed ACKs and 237 move-result events. Its last typed request is automatic EndTurn829, `own_turn=27`, reason `no_owned_hero`; its exact ACK is present. Re-extracting actual server-apply markers and rerunning the existing event contract returns valid with no event errors. That event check explicitly remains `real_execution_certified=false`; it is not a whole-game/normal-exit certificate.
- Raw lines69156–69164 show red Nullkiller2 continuing a Thorgrim mine plan, sending MoveHero867 and entering the synchronous wait for that request.
- Lines69168–69176 apply blue defeat and the Director's actual `game_over`. Lines69214–69223 apply red victory, including the actual NK `gameOver` callback. Both player endings are present.
- Lines69224 and69231 say `Auto-test shutdown deferred: pending native request acknowledgments`. The final battle's PackageApplied is still consumed at69226–69230; server-ready notifications follow, but no subsequent MoveHero receive/application appears for867.
- The old ACK-drain helper prints its all-players-ended/normal-shutdown marker only when the entire registry empties. That marker is absent here; the fact that both players have ended must not be conflated with that missing transport marker.

## Source chain explaining the dead wait

References below are the actual reviewed `/root/heroes3-ai-lab/src/vcmi-adv` tree, not the separate workspace `vcmi` tree.

1. `CGameHandler.cpp3988` recursively checks remaining players after a loss;3990–3997 finds no INGAME players and changes the server state to SHUTDOWN. There is also a no-active-player shutdown at `TurnOrderProcessor.cpp268–271`.
2. `CVCMIServer.cpp165–168` immediately calls `networkHandler->stop()` when entering SHUTDOWN. `lib/network/NetworkHandler.cpp108–110` stops the underlying IO context. `CVCMIServer::run`213–215 is that handler's event loop. The queued/new request cannot be expected to reach `onPacketReceived`141–149 and then `CGameHandler::handleReceivedPack` after this stop.
3. `CGameHandler::handleReceivedPack`509–555 produces PackageReceived/PackageApplied only for a pack it actually processes. A terminal-rejection ACK cannot be created simply by changing this visitor:867 is outside its receive path. A real server-rejection approach requires a new terminal server-drain lifecycle that continues receiving and rejects requests explicitly before stopping. That is a broader protocol change, not a missing ACK line that an auditor may synthesize.
4. `CClient::sendRequest` assigns/registers the actual request and, when `waitTillRealize` is set, calls `waitingRequest.waitWhileContains`. `ThreadSafeVector::waitWhileContains`, `Client.h73–79`, wakes only when the request is removed; it does not observe NK's own thread-interruption flag.
5. `AIGateway::gameOver`, `AI/Nullkiller2/AIGateway.cpp171–183`, does request AI-turn interruption for its player. That does not itself release the existing client wait. Hence all-player terminal notification and AI interruption can coexist with a blocked foreign request and a permanently nonempty global ACK registry.

## Recommended next isolated protocol

Prefer a **Director-owned real-request drain**, followed by normal terminal cleanup of foreign waits, over adding a whole server terminal-receive lifecycle merely for this headless close path. Scope this explicitly to the testing harness/new native epoch; do not replace the frozen old marker or silently reinterpret old `transport_drained` results.

- Add thread-safe actual request ownership/type bookkeeping, registered when the real native request ID/player are assigned and before dispatch. Track **all** Director-owned requests, including policy, query, economy, save and battle requests, rather than only selected moves. Real PackageApplied is the only ACK-completion path.
- Require actual test-mode all-player terminal state, actual owned game_over, and an empty Director-owned pending set before declaring the new owned-drain condition. A pending owned request remains a failed engineering case; no cancellation exception may certify it as executed.
- Record foreign pending IDs, owners and packet types in a distinct terminal-cleanup ledger. Call them cancelled waits/unverified foreign terminal requests, never successful applications or server ACKs. A request still pending at cleanup might have an ACK buffered, so cancellation must not automatically claim the action was never executed.
- Use a new marker describing the scope, for example `Ending game after Director native request drain; foreign waits pending terminal cleanup`. Do not print the old global-drain marker with altered meaning.
- Let the existing **normal shutdown** path cancel waits. `CClient::finishGameplay`145–151 already invokes `waitingRequest.requestTermination()` before asking interfaces to finish. `ThreadSafeVector::requestTermination`51–54 clears/notifies; `waitWhileContains`78–79 then throws `TerminationRequestedException`. This is explicit termination, not a fake successful callback. Do not merely erase foreign IDs and return from their synchronous waits as though the requests succeeded.
- Avoid calling `requestTermination` inside the receive callback while continuing to process buffered ACKs: `tryRemovingElement` asserts that termination has not started. Keep the established shutdown sequencing and verify clean process exit. Log actual cancellation in the termination path; an earlier shutdown-ready record is only an intention/remaining-waits snapshot.
- Preserve non-Director AI callback and gameplay timing until terminal cleanup. The prior Director-only request-binding repair remains separate.

## Required independent gates for implementation

The new auditor must bind the new scope/marker/version, all actual registered Director requests and real matching ACKs, the actual owned outcome/all-player terminal state, and exit0. It must reject cancellation of a Director request, false terminal state, foreign cancellation before the final outcome, owner mismatch, fake PackageApplied, shutdown with a pending owned query/economy/battle request, and any policy action after owned terminal. Foreign cancellation records are excluded from policy execution, rewards and training admission.

Reproduce this exact failed seed/candidate/model without removing its seed; require the published request/action and gameplay traces to agree with the old prefix, the same genuine terminal outcome, complete owned application/ACK proof, explicit foreign terminal cancellation and normal exit. Preserve both the old timeout and the new-run evidence. This fixes transport liveness only and cannot be advertised as improved strategy or a newly won game.
