# Python audit epoch v4: verified neutral battle ACK

Native source, all nine candidate payloads, candidate manifest, capsule03 and atomic closed-registry semantics remain exactly v3. This is a Python audit epoch; no native rebuild or new native qualification game.

Generic actual NativeRequestAck accepts player 0..7, plus NEUTRAL=-1 only for pack_type=198 and an earlier actual client send with the same ID and exact type 10MakeAction. Canonical decimal encoding is required. Director registrations and Director ACKs remain restricted to the actual owned player 0 or 1. Complete real ACK sets, success, packet type, order, atomic termination, compiled source attestation, frozen SHA and runtime identity checks remain strict. Other negative owners and unverified neutral packets are rejected.

New runner PLAN and EXECUTION explicitly identify director-neutral-makeaction-ack-v4. Independent read-only re-auditing of original untagged v3 inputs reports input_audit_epoch=legacy-v3-untagged and read_only_legacy_reaudit=true; original PLAN/EXECUTION/RESULT are unchanged. The original frozen v3 manifest must byte-match the local reused manifest. All nine native sources remain bound to capsule build-source-manifest and source-snapshot.

Parser requalification uses only the three completed terminal-drain qualification games and the completed pair02/a raw from failed paired03. Its independent four-raw gate records zero new native games. Original paired03 failure remains failed and unscored. Fresh paired04 must use v4 runner and auditors in both arms, same capsule03/checkpoint/seeds/method/proxy algorithm, after the gate is frozen.

CPU fixtures are artificial predicates, never native certificates. No GPU, optimizer, training, native execution or ability improvement is claimed. Atomic foreign wait clearing is not an ACK, successful application, or proof the foreign action never executed.
