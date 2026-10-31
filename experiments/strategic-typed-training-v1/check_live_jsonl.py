"""Meaningful split-write race cases for the observer, not native execution proofs."""
import json
from pathlib import Path
from live_jsonl import parse
raw=(json.dumps({'event':'busy_state','name':'英雄'})+'\n'+json.dumps({'event':'game_over','completed':True})+'\n').encode()
checked=0
for position in range(len(raw)+1):
    prefix=raw[:position];expected=prefix.count(b'\n');rows=parse(prefix)
    assert len(rows)==expected;checked+=1
assert len(parse(raw,final=True))==2
try:parse(raw[:-1],final=True)
except ValueError:pass
else:raise AssertionError('Uncommitted final tail accepted')
try:parse(b'{bad}\n')
except (ValueError,json.JSONDecodeError):pass
else:raise AssertionError('Malformed committed line skipped')
out=Path(__file__).parent/'live-jsonl-cpu-01';out.mkdir(exist_ok=False)
(out/'AUDIT.json').write_text(json.dumps({'passed':True,'split_positions':checked,'final_partial_rejected':True,'malformed_committed_rejected':True,'native_games':0,'optimizer_steps':0},indent=2))
print(json.dumps({'passed':True,'split_positions':checked}))
