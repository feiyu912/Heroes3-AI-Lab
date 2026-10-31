"""Audit monthly monster creation from native logs without loading engine state."""
import hashlib
import json
from pathlib import Path
import re
import sys


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    events, pending = [], []
    added = set()
    sent = 0
    creature = None
    with path.open(errors='replace') as stream:
        for lineno, line in enumerate(stream, 1):
            start = re.search(r'Spawning wandering monsters\. Found (\d+) free tiles\. Creature type: (\d+)', line)
            if start:
                creature = int(start[2])
            spawn = re.search(r'Spawning monster at \((\d+) (\d+) (\d+)\)', line)
            if spawn:
                pending.append(dict(line=lineno, position=list(map(int, spawn.groups())), creature_id=creature))
            turn = re.search(r'Info about turn (\d+) has been sent', line)
            if turn and pending:
                for event in pending:
                    event['day'] = int(turn[1])
                    events.append(event)
                pending.clear()
            obj = re.search(r'Added object id=(\d+); name=(creatures\.[^\s]+)', line)
            if obj:
                added.add((int(obj[1]), obj[2]))
            sent += 'Sending to all clients: 9NewObject' in line
    return dict(path=str(path), sha256=sha(path), spawns=events,
                unassigned_spawns=pending, creature_object_ids=len(added), new_object_broadcasts=sent)


original, replay, output = map(Path, sys.argv[1:4])
if output.exists():
    raise ValueError('Refuse overwrite')
audits = [read(path / 'client.log') for path in (original, replay)]
for audit in audits:
    audit['spawns_through_day1305'] = sum(e['day'] <= 1305 for e in audit['spawns'])
    audit['near_final_hero_through_day1305'] = [e for e in audit['spawns'] if e['day'] <= 1305 and
                                              abs(e['position'][0]-30) <= 2 and abs(e['position'][1]-18) <= 2]
prefixes = [[(e['day'], e['position'], e['creature_id']) for e in a['spawns'] if e['day'] <= 1305] for a in audits]
report = dict(diagnostic_only=True, audits=audits, spawn_prefix_through_day1305_equal=prefixes[0] == prefixes[1],
              conclusion='Native monthly monsters exist despite initially monster-free map, including guard at (29,16). DirectorAI has no Obj::MONSTER target branch. This establishes a missing legal strategic action class; complete frontier disconnection still needs visible guardian/path diagnostics.')
output.write_text(json.dumps(report, indent=2))
print(json.dumps({k:v for k,v in report.items() if k != 'audits'}, indent=2))
for a in audits:
    print(json.dumps({k:v for k,v in a.items() if k not in ('spawns','unassigned_spawns')}, indent=2))
