"""Isolated, seeded first-stage tactical maps; no prior final results accessed."""
import copy
import hashlib
import json
from pathlib import Path
import zipfile
import numpy as np
from lab_io import atomic_json


def main():
    here = Path(__file__).resolve().parent
    root = Path('/root/heroes3-ai-lab')
    rng = np.random.default_rng(2026102801)
    recipes = {
        'dragon-breath': [('greenDragon', 2, 6), ('pikeman', 20, 65),
                          ('archer', 12, 40), ('swordsman', 8, 25)],
        'retaliation-bait': [('pikeman', 1, 2), ('centaur', 1, 2),
                             ('swordsman', 25, 65), ('archer', 20, 55)],
        'death-cloud': [('lich', 10, 25), ('pikeman', 20, 60),
                        ('archer', 15, 40), ('skeleton', 25, 70)],
    }
    cases = []
    for tactic, recipe in recipes.items():
        for index in range(8):
            army = [{} for _ in range(7)]
            slots = rng.choice(7, 4, replace=False)
            for slot, (name, low, high) in zip(slots, recipe):
                army[int(slot)] = dict(type='core:' + name, amount=int(rng.integers(low, high)))
            armies = [army, copy.deepcopy(army)]
            split = 'train' if index < 4 else 'development' if index < 6 else 'test'
            name = f'lab/human-v1-{tactic}-{index:02d}.vmap'
            path = root / 'data/vcmi/Maps' / name
            with zipfile.ZipFile(root/'src/gym/maps/gym/ml-mini.vmap') as source, zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as target:
                for entry in source.namelist():
                    content = source.read(entry)
                    if entry == 'objects.json':
                        objects = json.loads(content)
                        for obj in objects.values():
                            if obj.get('type') == 'hero':
                                side = int(obj['options']['owner'] != 'red')
                                obj['options'].update(experience=0, primarySkills=dict(attack=0, defence=0, knowledge=0, spellpower=0), secondarySkills=[], spellBook=['preset'], army=armies[side])
                        content = json.dumps(objects).encode()
                    target.writestr(entry, content)
            with zipfile.ZipFile(path) as saved:
                heroes = [obj for obj in json.loads(saved.read('objects.json')).values() if obj.get('type') == 'hero']
            assert len(heroes) == 4 and all(obj['options']['army'] == army for obj in heroes)
            cases.append(dict(id=f'human-v1-{tactic}-{index:02d}', tactic_id=tactic,
                map=name, split=split, armies=armies, tight_formation_chance=100 if index % 2 == 0 else 0,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                supported_variations=['troop counts', 'slots', 'tight/loose formation', 'roles', 'engine seeds'],
                pending_variations=['arbitrary initial hexes', 'independent facing', 'obstacles', 'hero skills', 'unseen creature families']))
    assert len({json.dumps(case['armies'], sort_keys=True) for case in cases}) == len(cases)
    atomic_json(here/'scenarios.json', cases)
    atomic_json(here/'scenario-audit.json', dict(passed=True, maps=24, train=12,
        development=6, test=6, final_results_read=False, seed=2026102801,
        all_exact_mirrors=True, arbitrary_layouts_supported=False))
    print('24 actual maps verified: 12 train / 6 development / 6 test', flush=True)


if __name__ == '__main__':
    main()
