#!/usr/bin/env python3
"""Inspect native battle events of an events-v2 episode archive."""
import gzip
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
with gzip.open(path, 'rt') as f:
    data = json.load(f)

ep = data['episode']
print('episode:', ep['battle_id'], 'policy:', ep['policy'], 'success:', ep['success'])
print('steps:', ep['steps'], 'decisions_with_events:', ep['decisions_with_events'],
      'attacks:', ep['native_attacks'], 'counter:', ep['native_counter_attacks'],
      'secondary_hits:', ep['native_secondary_hits'])

KINDS = {0: 'ACTION_STARTED', 1: 'ACTION_FINISHED', 2: 'ATTACK', 3: 'BATTLE_END'}
ATYPES = {0: 'NO_ACTION', 1: 'END_TACTIC_PHASE', 2: 'RETREAT', 3: 'SURRENDER', 4: 'HERO_SPELL',
          5: 'WALK', 6: 'WAIT', 7: 'DEFEND', 8: 'WALK_AND_ATTACK', 9: 'SHOOT',
          10: 'CATAPULT', 11: 'MONSTER_SPELL', 12: 'BAD_MORALE', 13: 'STACK_HEAL', 14: 'WALK_AND_CAST'}
AFLAGS = {1: 'SHOT', 2: 'COUNTER', 4: 'LUCKY', 8: 'UNLUCKY', 16: 'BALLISTA', 32: 'DEATH_BLOW', 64: 'SPELL_LIKE'}
DFLAGS = {1: 'KILLED', 2: 'SECONDARY', 8: 'CLONE_KILLED', 16: 'SPELL_EFFECT'}

# unit id -> creature type, from the first decision that contains it
units = {}
for d in data['decisions']:
    for i, row in enumerate(d['observation']['nodes']['Unit']):
        # IS_ENEMY at index? just record the row for reference
        units[i] = row


def uname(uid):
    if uid is None or uid < 0:
        return f'uid{uid}'
    return f'uid{uid}'


# Show events around the first dragon breath: find ATTACK events with secondary targets
shown = 0
for di, d in enumerate(data['decisions']):
    for ev in d['battle_events']:
        if ev['kind'] != 2 or not any(t['flags'] & 2 for t in ev['targets']):
            continue
        flags = [n for b, n in AFLAGS.items() if ev['attack_flags'] & b]
        print(f"\n--- decision {di}: breath attack by uid{ev['attacker_id']} "
              f"(node {ev['attacker_node']}) flags={flags} tile={ev['attack_tile']}")
        for t in ev['targets']:
            tf = [n for b, n in DFLAGS.items() if t['flags'] & b]
            print(f"    target uid{t['defender_id']} (node {t['defender_node']}): "
                  f"dmg={t['damage']} killed={t['killed']} flags={tf} spell={t['spell_id']}")
        shown += 1
        if shown >= 6:
            break
    if shown >= 6:
        break

# summary of all attack events
print('\n=== all ATTACK events ===')
for di, d in enumerate(data['decisions']):
    for ev in d['battle_events']:
        if ev['kind'] != 2:
            continue
        flags = [n for b, n in AFLAGS.items() if ev['attack_flags'] & b]
        tg = ','.join(f"u{t['defender_id']}:{t['damage']}/{t['killed']}"
                      + ('*S' if t['flags'] & 2 else '') for t in ev['targets'])
        print(f"  d{di:3d} attacker=u{ev['attacker_id']:<3} flags={str(flags):<28} targets=[{tg}]")

print('\n=== ACTION events (first 12) ===')
n = 0
for di, d in enumerate(data['decisions']):
    for ev in d['battle_events']:
        if ev['kind'] not in (0, 1):
            continue
        print(f"  d{di:3d} {KINDS[ev['kind']]:<16} type={ATYPES.get(ev['action_type'])} "
              f"stack=u{ev['stack_number']} side={ev['side']} hexes={ev['target_hexes']}")
        n += 1
        if n >= 12:
            break
    if n >= 12:
        break

print('\n=== BATTLE_END ===')
for di, d in enumerate(data['decisions']):
    for ev in d['battle_events']:
        if ev['kind'] == 3:
            print(f"  d{di} result_type={ev['result_type']} winner={ev['winner']}")
