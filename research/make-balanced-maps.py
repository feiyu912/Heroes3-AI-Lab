"""Near-balanced ordinary battles: same unit types, varied armies and slots."""
from pathlib import Path
import hashlib
import json
import zipfile

root = Path('/root/heroes3-ai-lab')
source = root / 'src/gym/maps/gym/ml-mini.vmap'
pools = [ ['pikeman', 'archer', 'griffin'], ['centaur', 'woodElf', 'pegasus'],
          ['swordsman', 'monk', 'cavalier'], ['dwarf', 'woodElf', 'unicorn'],
          ['pikeman', 'monk', 'pegasus'], ['dendroidGuard', 'archer', 'griffin'] ]
scenarios = []
for i in range(36):
    split = 'train' if i < 20 else ('validation' if i < 26 else 'test')
    types = pools[i % len(pools)]
    amounts = [12 + i, 6 + i, 3 + i // 2]
    armies = []
    for side in range(2):
        army = []
        for j, creature in enumerate(types):
            delta = 0 if i % 3 == 0 else (1 if side == (i % 2) else -1)
            army.append(dict(amount=amounts[j] + delta, type='core:' + creature))
        slots = [0, 2, 5] if i % 2 == 0 else [1, 3, 6]
        placed = [{} for _ in range(7)]
        for slot, stack in zip(slots if side == 0 else slots[::-1], army):
            placed[slot] = stack
        armies.append(placed)
    name = f'lab/balanced-{i:02d}.vmap'
    target = root / 'data/vcmi/Maps' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as dst:
        for entry in src.namelist():
            data = src.read(entry)
            if entry == 'objects.json':
                objects = json.loads(data)
                for obj in objects.values():
                    if obj.get('type') != 'hero':
                        continue
                    options = obj['options']
                    side = int(options['owner'] != 'red')
                    options.update(experience=0,
                                   primarySkills=dict(attack=0, defence=0, knowledge=0, spellpower=0),
                                   secondarySkills=[], spellBook=['preset'], army=armies[side])
                data = json.dumps(objects).encode()
            dst.writestr(entry, data)
    scenarios.append(dict(id=f'balanced-{i:02d}', map=name, split=split, armies=armies,
                          sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                          random_obstacles=0, scope='same creature types and close counts; reversed deployment; no magic'))
Path('/mnt/g/Heroes3-AI-Lab/research/scenarios-v2.json').write_text(json.dumps(scenarios, indent=2))
print('Created 36 balanced army cases: 20 train / 6 validation / 10 test')
