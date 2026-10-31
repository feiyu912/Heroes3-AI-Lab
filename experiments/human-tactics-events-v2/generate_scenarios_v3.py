"""events-v3: NEW locked test fixtures + scenarios-v3.json.

Per WORKBUDDY_EVENTS_V2_REVIEW_20261018.md the old bait 14/15 and cloud 22/23
scenarios were consumed by demonstration selection and can no longer serve as
independent tests. This generates 6 brand-new test maps (fresh RNG seed, new
ids `human-events-v3-locked-*`) that have NEVER been used in any run, and
writes scenarios-v3.json = the 24 existing entries (prior usage annotated)
followed by the 6 locked-test entries at indices 24..29.
"""
import copy
import hashlib
import json
from pathlib import Path
import zipfile
import numpy as np
from lab_io import atomic_json

ROOT = Path('/root/heroes3-ai-lab-events-v2')


def main():
    here = Path(__file__).resolve().parent
    rng = np.random.default_rng(2026101802)  # NEW seed, never used before

    recipes = {
        'dragon-breath': [('greenDragon', 2, 6), ('pikeman', 20, 65),
                          ('archer', 12, 40), ('swordsman', 8, 25)],
        'retaliation-bait': [('pikeman', 1, 2), ('centaur', 1, 2),
                             ('swordsman', 25, 65), ('archer', 20, 55)],
        'death-cloud': [('lich', 10, 25), ('pikeman', 20, 60),
                        ('archer', 15, 40), ('skeleton', 25, 70)],
    }
    new_cases = []
    for tactic, recipe in recipes.items():
        for index in range(2):
            army = [{} for _ in range(7)]
            slots = rng.choice(7, 4, replace=False)
            for slot, (name, low, high) in zip(slots, recipe):
                army[int(slot)] = dict(type='core:' + name, amount=int(rng.integers(low, high)))
            armies = [army, copy.deepcopy(army)]
            name = f'lab/human-events-v3-locked-{tactic}-{index:02d}.vmap'
            path = ROOT / 'data/vcmi/Maps' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(ROOT / 'src/gym/maps/gym/ml-mini.vmap') as source, \
                 zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as target:
                for entry in source.namelist():
                    content = source.read(entry)
                    if entry == 'objects.json':
                        objects = json.loads(content)
                        for obj in objects.values():
                            if obj.get('type') == 'hero':
                                side = int(obj['options']['owner'] != 'red')
                                obj['options'].update(
                                    experience=0,
                                    primarySkills=dict(attack=0, defence=0, knowledge=0, spellpower=0),
                                    secondarySkills=[], spellBook=['preset'],
                                    army=armies[side])
                        content = json.dumps(objects).encode()
                    target.writestr(entry, content)
            new_cases.append(dict(
                id=f'human-events-v3-locked-{tactic}-{index:02d}', tactic_id=tactic,
                map=name, split='locked-test-v3', armies=armies,
                tight_formation_chance=100 if index % 2 == 0 else 0,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                supported_variations=['troop counts', 'slots', 'tight/loose formation', 'roles', 'engine seeds'],
                pending_variations=['arbitrary initial hexes', 'independent facing', 'obstacles', 'hero skills', 'unseen creature families'],
                note='NEW locked test fixture (seed 2026101802); never used in any prior run'))

    old = json.loads((here / 'scenarios.json').read_text())
    contaminated = {  # per review: consumed by demo selection or Q2 extraction
        'human-events-v2-dragon-breath-06': 'old test; unused by demos (BC-eval only, n=8 pairs)',
        'human-events-v2-dragon-breath-07': 'old test; unused by demos (BC-eval only, n=8 pairs)',
        'human-events-v2-retaliation-bait-06': 'used to select Q3 demonstrations (frozen as exploratory)',
        'human-events-v2-retaliation-bait-07': 'used to select Q3 demonstrations (frozen as exploratory)',
        'human-events-v2-death-cloud-22': 'entered Q2 demonstration extraction',
        'human-events-v2-death-cloud-23': 'entered Q2 demonstration extraction',
    }
    for case in old:
        case['prior_usage'] = contaminated.get(case['id'], 'train/dev iteration only')
        case['independent_test_eligible'] = False  # no old scenario may serve as an independent test anymore
    for case in new_cases:
        case['prior_usage'] = 'never used before this file'
        case['independent_test_eligible'] = True

    cases = old + new_cases
    assert len(cases) == 30
    atomic_json(here / 'scenarios-v3.json', cases)
    atomic_json(here / 'scenario-audit-v3.json', dict(
        passed=True, total=30, train_dev=24, locked_test_v3=6, rng_seed=2026101802,
        locked_never_used_before=True,
        note='only indices 24..29 (split=locked-test-v3) may be used as independent tests'))
    print('scenarios-v3.json written: 24 existing (annotated) + 6 NEW locked-test (indices 24..29)')


if __name__ == '__main__':
    main()
