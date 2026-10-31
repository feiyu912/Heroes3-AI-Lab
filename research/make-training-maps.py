from pathlib import Path
import json
import zipfile
import hashlib

root = Path('/root/heroes3-ai-lab')
source = root / 'src/gym/maps/gym/ml-mini.vmap'
creatures = ['pikeman', 'archer', 'griffin', 'swordsman', 'monk', 'cavalier',
             'centaur', 'dwarf', 'woodElf', 'pegasus', 'dendroidGuard', 'unicorn']
scenarios = []
# Entire army compositions are held out; roles share a scenario split.
for i in range(12):
    split = 'train' if i < 8 else ('validation' if i < 10 else 'test')
    armies = []
    for side in range(2):
        armies.append([{'amount': 8 + (i * 3 + side * 5 + j * 7) % 18,
                        'type': 'core:' + creatures[(i + j * 3 + side) % len(creatures)]}
                       for j in range(1 + i % 3)])
    name = f'lab/curriculum-{i:02d}.vmap'
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
                                   primarySkills={'attack': 0, 'defence': 0, 'knowledge': 0, 'spellpower': 0},
                                   secondarySkills=[], spellBook=['preset'],
                                   army=armies[side] + [{} for _ in range(7 - len(armies[side]))])
                data = json.dumps(objects).encode()
            dst.writestr(entry, data)
    scenarios.append(dict(id=f'curriculum-{i:02d}', map=name, split=split, armies=armies,
                          sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
Path('/mnt/g/Heroes3-AI-Lab/research/scenarios-v1.json').write_text(json.dumps(scenarios, indent=2))
print('Created', len(scenarios), 'no-magic multi-creature scenarios')
