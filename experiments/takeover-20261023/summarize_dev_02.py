"""Read-only descriptive breakdown of the 96-game DEV; no promotion inference."""
import json
from collections import Counter, defaultdict
from pathlib import Path

RUN = Path('/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-20261023-02')
raw = json.loads((RUN / 'DEV-RAW-AUDIT.json').read_text())['DEV']
print('keys:', sorted(raw.keys()))
print('pair keys:', sorted(raw['control_vs_candidate_pairs'][0].keys()))
print('first pair:', json.dumps(raw['control_vs_candidate_pairs'][0], indent=2))

pairs = raw['control_vs_candidate_pairs']
win_delta = Counter(p['win_delta'] for p in pairs)
by_opponent = defaultdict(Counter)
for p in pairs:
    by_opponent[p['opponent']][p['win_delta']] += 1
print('control_vs_candidate win_delta counts:', dict(win_delta))
print('by opponent:', {k: dict(v) for k, v in by_opponent.items()})

# The raw auditor may expose parent comparisons under other keys.
for key in sorted(raw.keys()):
    if key.endswith('_pairs'):
        print(key, len(raw[key]))
