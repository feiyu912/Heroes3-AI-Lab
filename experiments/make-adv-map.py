"""Derive a core-hero adventure map from a lab battle fixture.

The lab maps are real adventure maps (72x72 surface, towns at y=70, heroes at y=2) but their
hero templates are ml:hero_*, which forces the ML server plugin to load. That plugin refuses
any non-battle game ("Cannot track stats when randomHeroes is disabled"), so a strategic-layer
harness must use core heroes and run without the ml mod.

Only the hero identity is rewritten. Armies, positions, towns, terrain and victory conditions
are untouched, so the resulting map is the same tactical situation with a vanilla hero shell.
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

SOURCE = Path('/root/heroes3-ai-lab/data/vcmi/Maps/lab/diverse-192.vmap')
TARGET = Path('/root/heroes3-ai-lab/data/vcmi/Maps/adv/adv-arena-01.vmap')

# Castle / Rampart core heroes. Names must exist in the core H3 content.
RED = ['core:christian', 'core:tyris']
BLUE = ['core:orrin', 'core:valeska']


def main():
    if not SOURCE.exists():
        raise SystemExit(f'missing source map {SOURCE}')
    with zipfile.ZipFile(SOURCE) as z:
        header = json.loads(z.read('header.json'))
        objects = json.loads(z.read('objects.json'))
        terrain = json.loads(z.read('surface_terrain.json'))

    mapping = {}
    for player, heroes in (('red', RED), ('blue', BLUE)):
        entries = list((header['players'].get(player, {}).get('heroes') or {}).items())
        for index, (key, value) in enumerate(entries):
            new = heroes[index % len(heroes)]
            mapping[value['type']] = new
            value['type'] = new

    rewritten = 0
    for obj in objects.values():
        if obj.get('type') != 'hero':
            continue
        options = obj.setdefault('options', {})
        old = options.get('type')
        if old in mapping:
            options['type'] = mapping[old]
            rewritten += 1

    header['name'] = 'adv-arena-01'
    header['description'] = ('Strategic-layer harness map derived from lab/diverse-192.vmap. '
                             'Core heroes, same armies and placement; no ml mod required.')
    header['mods'] = None

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    tmp = TARGET.with_suffix('.vmap.tmp')
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as out:
        out.writestr('header.json', json.dumps(header, indent=2))
        out.writestr('objects.json', json.dumps(objects, indent=2))
        out.writestr('surface_terrain.json', json.dumps(terrain))
    shutil.move(tmp, TARGET)

    print(json.dumps(dict(target=str(TARGET), hero_types=mapping, hero_objects_rewritten=rewritten,
                          players={p: [h['type'] for h in (header['players'][p]['heroes'] or {}).values()]
                                   for p in ('red', 'blue')}), indent=2))


if __name__ == '__main__':
    main()
