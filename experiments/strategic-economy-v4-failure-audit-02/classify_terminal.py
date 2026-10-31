"""Distinguish an executed terminal visit with late ACK from a spurious action."""
import json
import hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

d=json.loads((HERE/'AUDIT.json').read_text())
tail=d['last_action_log_context']
received=[r for r in tail if'Received CPack of type 8MoveHero'in r['text']]
rejected=[r for r in tail if'Player is not allowed to perform this action!'in r['text']or'Got false in applying 8MoveHero'in r['text']]
executed=[r for r in tail if'Player 0 (red) wants to move hero 2'in r['text']or'DirectorAI: step finished'in r['text']
          or('TryMoveHero'in r['text']and r['line']>33883)]
server_terminal=[r for r in tail if'Sending to all clients: 14PlayerEndsGame'in r['text']]
client_terminal=[r for r in tail if'DirectorAI: native gameOver'in r['text']]
assert received and rejected and not executed and server_terminal and client_terminal
assert server_terminal[0]['line']<33882<client_terminal[0]['line']
result=dict(schema='terminal-action-classification-v1',
    classification='spurious_move_rejected_after_server_terminal_before_client_gameover',
    terminal_ack_only=False,terminal_visit_proof=False,allow_as_valid_transition=False,
    action_request_id=286,native_request_id=496,server_received=received,server_rejected=rejected,
    postrequest_native_execution_evidence=executed,server_terminal=server_terminal,client_terminal=client_terminal,
    evidence_sha256=sha(HERE/'AUDIT.json'),no_new_native_or_audit_rule_applied=True,
    required_change='Do not release strategic scheduling merely because movement query unblocks while a preceding QueryReply ACK and terminal pack are still pending. This is not solvable by accepting late terminal ACKs.')
target=HERE/'TERMINAL_CLASSIFICATION.json';assert not target.exists();target.write_text(json.dumps(result,indent=2))
print(json.dumps(result))
