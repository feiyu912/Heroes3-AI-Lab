#!/usr/bin/env python3
"""Prepare an events-v2 worker root (isolated runtime).

Derivative of the frozen research/prepare-worker.py (which hardcodes the
original lab root and is reused read-only elsewhere). Same layout:
worker/data/vcmi/{Data,Maps,Mods} -> runtime data symlinks + config files.
"""
import json
from pathlib import Path
import sys

root = Path('/root/heroes3-ai-lab-events-v2')
worker = Path(sys.argv[1]).resolve()
assert worker.is_relative_to(root / 'workers'), 'Worker must stay in the events-v2 workers directory'
data = worker / 'data/vcmi'
config = data / 'config'
config.mkdir(parents=True, exist_ok=True)
for name in ['Data', 'Maps', 'Mods']:
    link = data / name
    target = root / 'data/vcmi' / name
    if not link.exists():
        link.symlink_to(target, target_is_directory=True)
    assert link.resolve() == target.resolve()
(config / 'modSettings.json').write_text(json.dumps({
    'activePreset': 'default',
    'presets': {'default': {'mods': ['core', 'vcmi', 'ml'], 'settings': {}}}
}))
(config / 'settings.json').write_text(json.dumps({
    'mods': {'validation': 'off'},
    'general': {'music': 0, 'sound': 0},
    'adventure': {'enemyMoveTime': 25, 'heroMoveTime': 25}
}))
for name in ['persistentStorage.json', 'keyBindingsConfig.json']:
    (config / name).write_text('{}')
print('Worker data:', data)
