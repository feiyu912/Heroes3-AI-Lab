# Query-ACK barrier removes the exact spurious terminal action

The authorized single regression uses the original train02/red/EmptyAI,
seed2026101860, old continuous-2/update-2 checkpoint and identical broker/encoder.
It has285 requests and285 successful native movement ACK states. Every request
and action byte in the285-action real prefix matches acceptance-02's failed
run. The old extra286th resource-directed action is no longer produced.

Both native QueryReply submissions are successfully applied. There are no
move_failed/economy_failed states, must-answer-query messages, disallowed-action
messages or false server applications. The last movement is explicitly ACKed;
no terminal_ACK exception is used. No action occurs after native terminal.
The independent generic raw audit also passes all native/file/model/map checks,
legal consumption and transfer conservation. Director's native win is reported
as this engineering outcome, not a training update or independent improvement.

The only intended new native behavior holds advanceTurn while queryRequests
still contains an unconsumed QueryReply ACK. This complements the prior
queryResolved and movement-query guards: movement unblocking cannot now outrun
the preceding query ACK and terminal packet. The evidence demonstrates this
specific terminal-race fix, without claiming every possible server dialogue has
been exhaustively tested.

run-01/PROTOCOL.json preserves the fresh code/native/map/weight freeze.
FUNCTIONAL_AUDIT.json contains all285 byte-hash pairs, complete ACK/terminal
checks and final native log evidence. RAW_AUDIT.json records independent episode
verification. All previous failure reports and original comparison failures
remain unchanged; no legality or final-action gate was relaxed.

Per parent authorization, a new complete economy acceptance-03 begins only
after this regression passes, using fresh immutable inputs. It separately gates
four EmptyAI engineering cases before eight Nullkiller2 training-map development
games. BC eligibility0; economics remains scripted.
