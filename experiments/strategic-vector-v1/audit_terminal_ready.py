"""Read-only diagnosis of terminal followed by passive readiness telemetry."""
import hashlib
import json
from pathlib import Path
import re
import sys

source=Path(sys.argv[1]);output=Path(sys.argv[2])
if output.exists():raise ValueError('Refuse overwrite')
smoke=json.loads(source.read_text());native=smoke['native_result'];run=Path(native['run_dir'])
trace=run/'strategy-trace.jsonl';log=run/'client.log'
rows=[(n,json.loads(line)) for n,line in enumerate(trace.read_text().splitlines(),1)]
terminal=[(n,row) for n,row in rows if row['event']in ('victory','defeat')]
if len(terminal)!=1:raise ValueError('Expected one owned terminal event for this diagnostic')
line,state=terminal[0]
tail=[(n,row) for n,row in rows if n>line]
projection=lambda row:{k:v for k,v in row.items() if k!='event'}
pure=all(row['event']in ('native_battle_ready','native_movement_unblocked') and projection(row)==projection(state) for _,row in tail)
text=log.read_text(errors='replace').splitlines()
own='red'if state['player']==0 else 'blue'
marker=[n for n,t in enumerate(text,1) if f'DirectorAI: native gameOver player={own} 'in t]
new_actions=[dict(line=n,text=t) for n,t in enumerate(text,1) if marker and n>marker[-1] and
    re.search(r'DirectorAI: (?:step hero|build town|recruit town|hire|transfer)',t)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(source_summary=str(source),native_run=str(run),native_completed=native['completed'],native_winner=native['winner'],
    move_requests=native['moves_requested'],move_replies=native['move_replies'],
    log_sha256=sha(log),trace_sha256=sha(trace),runner_recorded_hashes_match=sha(log)==native['log_sha256'] and sha(trace)==native['strategy_trace_sha256'],
    terminal_line=line,terminal_event=state,post_terminal_rows=[dict(line=n,record=row)for n,row in tail],
    post_terminal_rows_are_only_passive_same_state_readiness=pure,own_gameover_log_lines=marker,
    new_director_actions_after_own_gameover=new_actions,
    diagnosis='A raw audit requiring the literal final record to be terminal can reject passive readiness telemetry. Preserve the real terminal and separately prove no post-terminal action/resource change; this diagnostic does not authorize acceptance or training.')
output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
