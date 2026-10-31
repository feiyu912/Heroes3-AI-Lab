import json
from pathlib import Path
import sys
from collections import Counter

run = Path(sys.argv[1])
choices = [json.loads(s) for s in (run / 'strategy-decisions.jsonl').open()]
states = [json.loads(s) for s in (run / 'strategy-trace.jsonl').open()]
index = -1
counts = Counter()
examples = []
for state in states:
    if state['event'] == 'before_move':
        index += 1
    if state['event'] != 'move_applied' or index < 0 or index >= len(choices):
        continue
    choice = choices[index]
    hero = next((h for h in state['heroes'] if h['id'] == choice['hero']), None)
    if not hero:
        counts['hero_missing'] += 1
        continue
    actual = [hero[k] for k in ['x', 'y', 'z']]
    delta = tuple(a - b for a, b in zip(actual, choice['step']))
    counts[str(delta)] += 1
    if delta != (0, 0, 0) and len(examples) < 12:
        examples.append(dict(choice=choice, actual=actual, event=state['event']))
print(json.dumps(dict(counts=counts, examples=examples), indent=2))
