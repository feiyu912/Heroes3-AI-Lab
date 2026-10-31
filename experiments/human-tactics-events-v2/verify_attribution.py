#!/usr/bin/env python3
"""Verify v3 attribution: our executed action's attack groups only."""
import gzip
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
with gzip.open(path, 'rt') as f:
    data = json.load(f)

ep = data['episode']
our_side = 1 if ep['role'] == 'defender' else 0
ATYPES = {0: 'NO_ACTION', 5: 'WALK', 6: 'WAIT', 7: 'DEFEND', 8: 'WALK_AND_ATTACK', 9: 'SHOOT'}

checked = 0
for s in data['step_log']:
    post = s['post_events']
    action_attacks = s['action_attack_groups']
    followup = s['followup_own_attack_groups']
    window_enemy = s['window_enemy_attack_groups']
    our_starts = [i for i, e in enumerate(post) if e['kind'] == 0 and e.get('side', -1) == our_side]
    assert len(our_starts) <= 1, f"seq {s['seq']}: our side acted {len(our_starts)} times in one step"
    if our_starts:
        begin = our_starts[0]
        atype = post[begin]['action_type']
        stack = post[begin].get('stack_number')
        # locate matching finish
        fin = None
        for i in range(begin + 1, len(post)):
            e = post[i]
            if e['kind'] == 1 and e.get('side') == our_side and e.get('stack_number') == stack:
                fin = i
                break
        inwin = post[begin + 1:fin] if fin is not None else post[begin + 1:]
        # every action attack must be inside the window and ours
        for e in action_attacks:
            assert e in inwin, f"seq {s['seq']}: action attack outside our action window"
            assert e.get('attacker_side') == our_side
        # every followup must be after the finish
        for e in followup:
            assert fin is not None and post.index(e) > fin, f"seq {s['seq']}: followup inside window"
        if action_attacks:
            checked += 1
            print(f"seq {s['seq']:3d}: {ATYPES.get(atype):16s} -> {len(action_attacks)} action attack(s), "
                  f"{len(followup)} auto-retaliation(s), {len(window_enemy)} enemy attack(s) in window")

print(f"\nsteps with action attacks: {checked}")
print(f"reset events: {len(data.get('reset_events', []))}, "
      f"terminal events: {len(data.get('terminal_events', []))}")
term = [e for e in data.get('terminal_events', []) if e['kind'] == 3]
print(f"BATTLE_END events archived: {len(term)}")
