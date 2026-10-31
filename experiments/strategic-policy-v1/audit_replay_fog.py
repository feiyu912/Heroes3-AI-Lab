"""Compare native reveal packets with later visible-frontier requests, read-only."""
import hashlib
import json
from pathlib import Path
import re
import sys
from collections import Counter

run, rollout, out = map(Path, sys.argv[1:4])
if out.exists():
    raise ValueError('Refuse overwrite')
rows = [json.loads(line) for line in rollout.open()]
revealed = set()
step = -1
seen_packet = False
packets = repeated = violations = 0
nonempty = 0
movement_results = Counter()
examples = []
last_packet = None
with (run / 'client.log').open(errors='replace') as log:
    for lineno, line in enumerate(log, 1):
        if 'DirectorAI: step hero' in line:
            step += 1
            seen_packet = False
            if step >= len(rows):
                continue
            req = rows[step]['request']
            for c in req['candidates']:
                if c['kind'] != 5:
                    continue
                x, y, z = c['position']
                neighbors = {(x+dx, y+dy, z) for dx in range(-1, 2) for dy in range(-1, 2)
                             if 0 <= x+dx < 36 and 0 <= y+dy < 36}
                if neighbors <= revealed:
                    violations += 1
                    if len(examples) < 8:
                        examples.append(dict(step=step+1, day=req['day'], line=lineno,
                                             frontier=c['position'], neighbors_all_in_prior_native_reveals=True))
        if 'OI 0,' in line and ', fow ' in line and not seen_packet:
            seen_packet = True
            tiles = {tuple(map(int, parts)) for parts in re.findall(r'\((-?\d+) (-?\d+) (-?\d+)\)', line.split(', fow ', 1)[1])}
            packets += 1
            movement_results[re.search(r', res (\d+),', line)[1]] += 1
            nonempty += bool(tiles)
            if tiles and tiles <= revealed:
                repeated += 1
                last_packet = dict(step=step+1, line=lineno, tiles_count=len(tiles), tiles=sorted(tiles))
            revealed.update(tiles)
report = dict(run=str(run), rollout=str(rollout), diagnostic_only=True,
              native_packets_first_per_move=packets, revealed_union_size=len(revealed),
              native_packets_nonempty_reveals=nonempty, native_result_counts=dict(movement_results),
              packets_entirely_previously_revealed=repeated,
              frontier_candidates_all_neighbors_previously_revealed=violations,
              examples=examples, last_repeated_packet=last_packet,
              enemy_hero_tile_ever_in_reveal=(29,10,0) in revealed,
              limitation='Logged reveal union is monotonic audit reference, not proof engine never legitimately re-hid tiles; inspect FoWChange and snapshot replacement before causality claim.')
selected = [row['request']['candidates'][row['action']] for row in rows]
unfinished = [i for i, c in enumerate(selected[:-1]) if c['position'] != c['next']]
report['selected_remote_goal_before_next_decision'] = len(unfinished)
report['remote_goal_changed_next_decision'] = sum(selected[i]['position'] != selected[i+1]['position'] for i in unfinished)
report['consecutive_decision_actual_origin_changes'] = sum(a['request']['from'] != b['request']['from'] for a, b in zip(rows, rows[1:]))
report['consecutive_actual_origin_unchanged'] = sum(a['request']['from'] == b['request']['from'] for a, b in zip(rows, rows[1:]))
out.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
