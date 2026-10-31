# Baseline fifth game: duplicate-stack aggregation audit failure

native-pilot-01/baseline remains failed. Four first-map games passed strict audit (1win,3losses). The fifth game, training02 red seed2026101881, completed normally at day80 with767 movements requested/confirmed and0failed replies; the original shared raw auditor failed at army-transfer conservation before the sixth game was launched. The runner exited naturally; no candidate was installed or compiled and no further games were started.

The error is in audit_supply_raw.py army(): Counter({creature:count for creature,count in state['army']}) overwrites earlier stacks of the same creature. Such multiple stacks are legal, and this hero really has three archer stacks. It must aggregate counts across all slots; splitting/merging same-type slots must not create or destroy army value in an audit.

Native trace2256 before_army_transfer (day51,hero21,town18): hero archers[6,4,6],town archers36. Trace2257 economy_applied: hero archers[42,4,6],town archers0. Correct totals are hero16→52 (+36),town36→0 (−36), exactly conserved. Old helper sees hero6→6, so it reports no hero gain and raises Ambiguous transfer state. Other creature stacks remain unchanged. Source creature stack data is not malformed and should not be collapsed or edited in evidence.

Chronological economic action108 binds this state pair to native request2321: client.log172678 sends13ArrangeStacks request2321,172681 receives it at server,172692 reports successfully applied,172699 consumes Director economy ACK2321success1. Thus this transfer has actual native execution evidence, not only a client success flag.

Raw native directory: `/root/heroes3-ai-lab/workers/adv-runs/threat-a-native-pilot-01-baseline-4-2026101881-g2841epm`.

- client.log SHA256:e9aefc22c5d046d9e8f01f79948afaa7dafc48804178c4298ea5168591c950f7
- strategy-trace.jsonl SHA256:f4848e134f66ed6e92c0f9241bf0da8a7dc45480b76370f59606274c45622d11
- strategy-decisions.jsonl SHA256:e3137cb0f6e30bc28fdd5347184079da80e79e32e222771f401692a5715fc6c3

Proposed repair is limited to the auditor's creature aggregation plus meaningful duplicate-slot/reorder/split-merge/genuine nonconservation tests. Do not change native training, candidate release logic or frozen native inputs. Keep the original failed batch and its source snapshot. Any corrected re-audit or continuation/rerun must use an explicit new audit/protocol version and preserve all originally selected seeds, rather than deleting the difficult fifth game or choosing new favorable seeds. This report itself does not modify the auditor or recertify the incomplete baseline stage.
