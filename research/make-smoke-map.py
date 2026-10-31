from pathlib import Path
import json
import zipfile

root = Path('/root/heroes3-ai-lab')
source = root / 'src/gym/maps/gym/ml-mini.vmap'
target = root / 'data/vcmi/Maps/lab/smoke.vmap'
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists():
    print(target)
    raise SystemExit(0)
with zipfile.ZipFile(source) as src, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as dst:
    for name in src.namelist():
        data = src.read(name)
        if name == 'objects.json':
            objects = json.loads(data)
            for obj in objects.values():
                if obj.get('type') != 'hero':
                    continue
                options = obj['options']
                options['experience'] = 0
                options['primarySkills'] = {'attack': 0, 'defence': 0, 'knowledge': 0, 'spellpower': 0}
                options['secondarySkills'] = []
                options['spellBook'] = ['preset']
                options['army'] = [{'amount': 20 if options['owner'] == 'red' else 10,
                                    'type': 'core:archer'}] + [{} for _ in range(6)]
            data = json.dumps(objects).encode()
        dst.writestr(name, data)
print(target)
