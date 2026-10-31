"""Six deterministic 36x36 strategic maps; no game runs, no existing-map rewrites."""
import argparse
import copy
from collections import Counter, deque
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
ENGINE = Path('/root/heroes3-ai-lab/src/vcmi-adv')
BASE = ROOT.parent / 'fixtures/maps/takeover-economy-36-v1.vmap'
SPECS = [
    dict(name='takeover-v2-train-01-mines', split='train', minimal=True, gold=600, materials=6, guards=0, delta=0),
    dict(name='takeover-v2-train-02-development', split='train', minimal=False, gold=800, materials=7, guards=6, delta=0),
    dict(name='takeover-v2-dev-01-river', split='dev', minimal=False, gold=700, materials=8, guards=8, delta=1, water=True),
    dict(name='takeover-v2-dev-02-reserves', split='dev', minimal=False, gold=1000, materials=6, guards=10, delta=2),
    dict(name='takeover-v2-test-01-river', split='test', minimal=False, gold=900, materials=9, guards=9, delta=0, water=True),
    dict(name='takeover-v2-test-02-reserves', split='test', minimal=False, gold=1200, materials=8, guards=12, delta=1),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def deterministic_zip(path, members):
    with zipfile.ZipFile(path, 'w') as z:
        for name, value in members.items():
            entry = zipfile.ZipInfo(name, (2026, 10, 18, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, json.dumps(value, sort_keys=True, separators=(',', ':')))


def footprint(obj, chars):
    rows = obj['template']['mask']
    cells = set()
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char in chars:
                cells.add((obj['x'] - (len(row) - 1 - x), obj['y'] - (len(rows) - 1 - y)))
    return cells


def static_reachable(terrain, objects, start):
    blocked = set().union(*(footprint(obj, 'BH') for obj in objects.values()))
    queue, seen = deque([start]), {start}
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nxt = x + dx, y + dy
            if (0 <= nxt[0] < 36 and 0 <= nxt[1] < 36 and nxt not in seen
                    and nxt not in blocked and not terrain[nxt[1]][nxt[0]].startswith('wt')):
                seen.add(nxt)
                queue.append(nxt)
    return seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--minimal-only', action='store_true')
    parser.add_argument('--install-dir', type=Path, default=Path('/root/heroes3-ai-lab/data/vcmi/Maps/adv'))
    args = parser.parse_args()
    with zipfile.ZipFile(BASE) as archive:
        base_header = json.loads(archive.read('header.json'))
        base_objects = json.loads(archive.read('objects.json'))
    templates = json.loads((ROOT / 'core-template-audit.json').read_text())['templates']
    audit = {'schema': 'strategic-development-map-suite-v2', 'base_sha256': sha(BASE),
             'generator_sha256': sha(Path(__file__)), 'template_audit_sha256': sha(ROOT / 'core-template-audit.json'),
             'split_frozen_before_outcomes': True, 'engine_executed_by_generator': False,
             'status': 'STATIC_CHECKED_ENGINE_ACCEPTANCE_PENDING',
             'source_hashes': {}, 'maps': []}
    for relative in ['config/objects/moddables.json', 'lib/mapObjects/MiscObjects.cpp',
                     'lib/mapObjects/CGResource.cpp', 'lib/mapObjects/CGCreature.cpp',
                     'lib/mapObjects/ObjectTemplate.cpp', 'lib/mapObjects/army/CArmedInstance.cpp']:
        audit['source_hashes'][relative] = sha(ENGINE / relative)
    selected = SPECS[:1] if args.minimal_only else SPECS
    for spec in selected:
        header, objects = copy.deepcopy(base_header), copy.deepcopy(base_objects)
        header['name'] = spec['name']
        header['description'] = 'Normal 1v1 strategic development map. Public exploration, resources, mines, recruitment and optional expansion. No scripted grants.'
        # Symmetric visit coordinates, common native template orientation; hero identities differ.
        for index, (anchor_x, hero_x) in enumerate(((8, 7), (31, 30))):
            objects[f'town_{index}'].update(x=anchor_x, y=8)
            objects[f'hero_{index}'].update(x=hero_x, y=10)
        added = []

        def add(key, kind, subtype, visit_x, visit_y, template, options, mirrored_pair=None):
            rows = template['mask']
            visits = [(x, y) for y, row in enumerate(rows) for x, char in enumerate(row) if char == 'A']
            assert len(visits) == 1
            vx, vy = visits[0]
            obj = dict(type=kind, subtype=subtype, l=0,
                       x=visit_x + len(rows[vy]) - 1 - vx,
                       y=visit_y + len(rows) - 1 - vy,
                       template=copy.deepcopy(template), options=copy.deepcopy(options))
            objects[key] = obj
            added.append(dict(key=key, type=kind, subtype=subtype, visitable=[visit_x, visit_y],
                              paired_with=mirrored_pair))

        d = spec['delta']
        for side, mirror in (('left', False), ('right', True)):
            mx = lambda x: 35 - x if mirror else x
            for resource, x, y, animation, amount in (
                ('gold', 9, 11 + d, 'AVTgold0.def', spec['gold']),
                ('wood', 4, 12 + d, 'AVTwood0.def', spec['materials']),
                ('ore', 9, 15 + d, 'AVTore0.def', spec['materials'])):
                add(f'resource_{side}_{resource}', 'resource', f'core:{resource}', mx(x), y,
                    dict(animation=animation, editorAnimation='', mask=['VA'], visitableFrom=['+++', '+-+', '+++']),
                    {'amount': amount}, f'resource_{"left" if mirror else "right"}_{resource}')
            for subtype, x, y in [('sawmill', 6, 15 + d), ('orePit', 12, 12 + d)]:
                add(f'mine_{side}_{subtype}', 'mine', f'core:{subtype}', mx(x), y,
                    templates[subtype]['template'], {'owner': None, 'army': []},
                    f'mine_{"left" if mirror else "right"}_{subtype}')
            if not spec['minimal']:
                add(f'mine_{side}_goldMine', 'mine', 'core:goldMine', mx(12), 20 + d,
                    templates['goldMine']['template'],
                    {'owner': None, 'army': [{'type': 'core:pikeman', 'amount': spec['guards']}]},
                    f'mine_{"left" if mirror else "right"}_goldMine')
                add(f'neutral_town_{side}', 'town', 'castle', mx(12), 29,
                    base_objects['town_0']['template'],
                    {'owner': None, 'buildings': {'allOf': ['core:villageHall', 'core:dwellingLvl1']},
                     'army': [{'type': 'core:pikeman', 'amount': spec['guards'] + 4}], 'tightFormation': 'wide'},
                    f'neutral_town_{"left" if mirror else "right"}')
                add(f'guard_{side}', 'monster', 'core:pikeman', mx(7), 23 + d,
                    templates['pikeman']['template'],
                    {'amount': spec['guards'], 'character': 'savage', 'noGrowing': True,
                     'neverFlees': True, 'upgradedStackPresence': 'never'},
                    f'guard_{"left" if mirror else "right"}')
        terrain = [['sa0_' for _ in range(36)] for _ in range(36)]
        if spec.get('water'):
            for y in range(12, 24):
                for x in (17, 18):
                    terrain[y][x] = 'wt8|'
        assert all(row == list(reversed(row)) for row in terrain)
        for entry in added:
            pair = next(item for item in added if item['key'] == entry['paired_with'])
            assert entry['visitable'][0] + pair['visitable'][0] == 35
            assert entry['visitable'][1] == pair['visitable'][1]
            assert objects[entry['key']]['options'] == objects[pair['key']]['options']
        assert objects['hero_0']['options']['army'] == objects['hero_1']['options']['army']
        assert objects['town_0']['options']['buildings'] == objects['town_1']['options']['buildings']
        blocking = {}
        for key, obj in objects.items():
            for point in footprint(obj, 'BAHT'):
                assert all(0 <= value < 36 for value in point), (key, point)
                assert not terrain[point[1]][point[0]].startswith('wt'), (key, point)
                assert point not in blocking, (key, blocking.get(point), point)
                blocking[point] = key
        reachable = static_reachable(terrain, objects, (6, 10))
        for key, obj in objects.items():
            assert footprint(obj, 'AT') <= reachable, ('unreachable coarse terrain/object mask', key)
        destination = ROOT / 'maps' / (spec['name'] + '.vmap')
        destination.parent.mkdir(exist_ok=True)
        members = {'header.json': header, 'objects.json': objects, 'surface_terrain.json': terrain}
        deterministic_zip(destination, members)
        source_dir = ROOT / 'sources' / spec['name']
        source_dir.mkdir(parents=True, exist_ok=True)
        for filename, value in members.items():
            (source_dir / filename).write_text(json.dumps(value, indent=2))
        with zipfile.ZipFile(destination) as archive:
            assert archive.testzip() is None
            assert json.loads(archive.read('objects.json')) == objects
        args.install_dir.mkdir(parents=True, exist_ok=True)
        target = args.install_dir / destination.name
        if target.exists() and sha(target) != sha(destination):
            raise RuntimeError(f'Install refuses different existing map: {target}')
        target.write_bytes(destination.read_bytes())
        audit['maps'].append(dict(spec=spec, path=str(destination), installed_path=str(target),
            resource_name='Maps/adv/' + spec['name'], sha256=sha(destination),
            object_counts=dict(Counter(obj['type'] for obj in objects.values())),
            added_objects=added, old_map_not_modified=True, engine_load_verified=False,
            static_reachable_cells=len(reachable), actual_native_path_not_computed=True,
            paired_value_and_visitable_position_symmetry_checked=True,
            starting_army_and_buildings_equal=True,
            exact_path_cost_symmetry_claimed=False,
            hero_specialties_equal=False))
    manifest = ROOT / ('minimal-audit.json' if args.minimal_only else 'suite-audit.json')
    manifest.write_text(json.dumps(audit, indent=2))
    print(json.dumps({'manifest': str(manifest), 'maps': [entry['resource_name'] for entry in audit['maps']],
                      'engine_executed': False}, indent=2))


if __name__ == '__main__':
    main()
