"""Prepare tactical affordances, without claiming demonstrations or learned skills."""
import copy
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
from lab_io import atomic_json


def main():
    root = Path('/root/heroes3-ai-lab')
    research = Path(__file__).resolve().parent
    template = root / 'src/gym/maps/gym/ml-mini.vmap'
    rng = np.random.default_rng(2026102601)
    families = {
        'guard-shooters': [('archer', 15, 65), ('pikeman', 25, 90),
                           ('swordsman', 8, 35), ('griffin', 8, 35)],
        'expendable-retaliation': [('pikeman', 1, 2), ('pikeman', 1, 2),
                                  ('swordsman', 20, 70), ('archer', 15, 60)],
        'split-focus': [('archer', 12, 45), ('archer', 12, 45),
                        ('pikeman', 25, 85), ('cavalier', 5, 25)],
    }
    # All new maps have four stacks; existing three-stack final fixtures are
    # neither read nor used to choose the exercises or their troop sizes.
    cases = []
    fingerprints = set()
    for family, stacks in families.items():
        for index in range(40):
            while True:
                army = [{} for _ in range(7)]
                slots = rng.choice(7, len(stacks), replace=False)
                for slot, (creature, low, high) in zip(slots, stacks):
                    army[int(slot)] = dict(type='core:' + creature,
                                           amount=int(rng.integers(low, high)))
                fingerprint = json.dumps(army, sort_keys=True)
                if fingerprint not in fingerprints:
                    fingerprints.add(fingerprint)
                    break
            armies = [army, copy.deepcopy(army)]
            name = f'lab/tactical-{family}-{index:02d}.vmap'
            destination = root / 'data/vcmi/Maps' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(template) as source, zipfile.ZipFile(
                    destination, 'w', zipfile.ZIP_DEFLATED) as target:
                for entry in source.namelist():
                    content = source.read(entry)
                    if entry == 'objects.json':
                        objects = json.loads(content)
                        for obj in objects.values():
                            if obj.get('type') == 'hero':
                                side = int(obj['options']['owner'] != 'red')
                                obj['options'].update(
                                    experience=0, primarySkills=dict(attack=0, defence=0,
                                        knowledge=0, spellpower=0), secondarySkills=[],
                                    spellBook=['preset'], army=armies[side])
                        content = json.dumps(objects).encode()
                    target.writestr(entry, content)
            cases.append(dict(id=f'tactical-{family}-{index:02d}', map=name,
                split='train' if index < 32 else 'development', family=family,
                armies=armies, sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                scope='Exact mirror; four preconfigured stacks; tactical opportunity, not an expert action label'))
    atomic_json(research / 'tactical-curriculum.json', cases)
    ordinary = json.loads((research / 'diverse-curriculum.json').read_text())
    atomic_json(research / 'mixed-tactical-curriculum.json', ordinary + cases)
    # Verify actual saved map contents, not only the in-memory recipe.
    for case in cases:
        with zipfile.ZipFile(root / 'data/vcmi/Maps' / case['map']) as archive:
            heroes = [obj for obj in json.loads(archive.read('objects.json')).values()
                      if obj.get('type') == 'hero']
        assert len(heroes) == 4
        for hero in heroes:
            assert hero['options']['army'] == case['armies'][int(hero['options']['owner'] != 'red')]
            assert not any(hero['options']['primarySkills'].values())
        assert case['armies'][0] == case['armies'][1]
        assert sum(bool(stack) for stack in case['armies'][0]) == 4
    audit = dict(passed=True, maps_verified=len(cases), train_cases=96,
        development_cases=24, mixed_training_cases=288, seed=2026102601,
        families=list(families), final_fixtures_read=False, final_results_read=False,
        expert_demonstrations=False, trained_on_these_maps=False,
        interpretation='Prepared only. Bait splitting is initial deployment, not an available policy action. No claim that any tactic has been learned or that any action is optimal.')
    atomic_json(research / 'tactical-curriculum-audit.json', audit)
    print(json.dumps(audit), flush=True)


if __name__ == '__main__':
    main()
