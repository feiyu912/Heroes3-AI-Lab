"""Deterministic, isolated adventure fixtures. Static validation is not engine acceptance."""
import argparse
import copy
import hashlib
import json
from collections import deque
from pathlib import Path
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_zip(path, members):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, value in members.items():
            info = zipfile.ZipInfo(name, (2026, 10, 18, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, json.dumps(value, sort_keys=True, separators=(',', ':')))


def ground_distance(terrain, start, finish):
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        (x, y), depth = queue.popleft()
        if (x, y) == finish:
            return depth
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nxt = (x + dx, y + dy)
            if (0 <= nxt[0] < 36 and 0 <= nxt[1] < 36 and nxt not in seen
                    and not terrain[nxt[1]][nxt[0]].startswith('wt')):
                seen.add(nxt)
                queue.append((nxt, depth + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, default=Path('/root/heroes3-ai-lab/data/vcmi/Maps/adv/adv-arena-01.vmap'))
    ap.add_argument('--install-dir', type=Path)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent
    out = root / 'maps'
    out.mkdir(exist_ok=True)
    with zipfile.ZipFile(args.source) as z:
        original_header = json.loads(z.read('header.json'))
        original_objects = json.loads(z.read('objects.json'))
    audit = {'source': str(args.source), 'source_sha256': digest(args.source),
             'generator_sha256': digest(Path(__file__)), 'engine_executed': False,
             'status': 'STATIC_CHECKED_ENGINE_LOAD_PENDING', 'maps': []}
    for mode in ('open', 'detour', 'economy'):
        name = f'takeover-{mode}-36-v1'
        header = copy.deepcopy(original_header)
        header['name'] = name
        header['description'] = ('Isolated strategic interface acceptance fixture, 36x36, '
            'one Castle and one core Knight per side. Development only; not a held-out test.')
        header['mapLevels']['surface'].update(width=36, height=36)
        header['players'] = {}
        objects = {}
        hero_positions = [(9, 18), (29, 18)] if mode != 'economy' else [(7, 10), (31, 30)]
        town_positions = [(8, 8), (32, 28)]
        for index, (color, hero_type) in enumerate((('red', 'core:christian'), ('blue', 'core:sorsha'))):
            hero_key, town_key = f'hero_{index}', f'town_{index}'
            header['players'][color] = {'canPlay': 'PlayerOrAI', 'heroes': {hero_key: {'type': hero_type}}}
            hero = copy.deepcopy(original_objects['hero_0'])
            hero.update(x=hero_positions[index][0], y=hero_positions[index][1], subtype='core:knight')
            hero['options'].update(type=hero_type, owner=color, name=f'{color} strategic hero',
                army=[{'type': 'core:pikeman', 'amount': 20}, {'type': 'core:archer', 'amount': 10}],
                primarySkills={'attack': 0, 'defence': 0, 'knowledge': 0, 'spellpower': 0},
                secondarySkills=[], spellBook=['preset'])
            objects[hero_key] = hero
            town = copy.deepcopy(original_objects['town_0'])
            town.update(x=town_positions[index][0], y=town_positions[index][1])
            buildings = ['core:fort', 'core:villageHall', 'core:tavern', 'core:dwellingLvl1']
            if mode == 'economy':
                buildings += ['core:townHall', 'core:dwellingLvl2']
            town['options'].update(owner=color, buildings={'allOf': buildings})
            objects[town_key] = town
        # Reuse known-valid original terrain tokens; no new graphic object guesses.
        terrain = [['sa0_' for _ in range(36)] for _ in range(36)]
        if mode == 'detour':
            for y in range(8, 28):
                for x in (17, 18):
                    terrain[y][x] = 'wt8|'
        source_dir = root / 'sources' / name
        source_dir.mkdir(parents=True, exist_ok=True)
        members = {'header.json': header, 'objects.json': objects, 'surface_terrain.json': terrain}
        for filename, value in members.items():
            (source_dir / filename).write_text(json.dumps(value, indent=2), encoding='utf-8')
        path = out / f'{name}.vmap'
        write_zip(path, members)
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            assert json.loads(z.read('objects.json')) == objects
        assert len(objects) == 4
        assert all(0 <= obj['x'] < 36 and 0 <= obj['y'] < 36 for obj in objects.values())
        assert objects['hero_0']['options']['army'] == objects['hero_1']['options']['army']
        assert objects['town_0']['options']['buildings'] == objects['town_1']['options']['buildings']
        start = (hero_positions[0][0]-1, hero_positions[0][1])
        end = (hero_positions[1][0]-1, hero_positions[1][1])
        distance = ground_distance(terrain, start, end)
        assert distance is not None
        if mode == 'detour':
            assert distance > abs(start[0] - end[0]) + abs(start[1] - end[1])
        entry = {'name': name, 'resource_name': f'Maps/adv/{name}', 'path': str(path),
                 'sha256': digest(path), 'dimensions': [36, 36, 1], 'players': 2,
                 'heroes_per_player': 1, 'towns_per_player': 1,
                 'hero_anchor_positions': hero_positions, 'hero_visitable_positions': [start, end],
                 'water_cells': sum(token.startswith('wt') for row in terrain for token in row),
                 'static_cardinal_terrain_distance': distance,
                 'static_distance_is_not_engine_path': True, 'engine_load_verified': False,
                 'resource_policy': 'Engine normal-difficulty equal starting resources; no script grants',
                 'town_buildings': buildings}
        if args.install_dir:
            args.install_dir.mkdir(parents=True, exist_ok=True)
            target = args.install_dir / path.name
            if target.exists() and digest(target) != digest(path):
                raise RuntimeError(f'Refusing to overwrite different existing map: {target}')
            target.write_bytes(path.read_bytes())
            entry['installed_path'] = str(target)
        audit['maps'].append(entry)
    (root / 'fixture-audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
