#!/usr/bin/env bash
cd / && /root/heroes3-ai-lab/venv/bin/python - <<'PY'
import json, zipfile
p = '/root/heroes3-ai-lab/data/vcmi/Maps/lab/diverse-192.vmap'
with zipfile.ZipFile(p) as z:
    o = json.loads(z.read('objects.json'))
    h = json.loads(z.read('header.json'))
for k in ['town_0', 'hero_0', 'creatureBank_8']:
    print('==', k)
    print(json.dumps(o[k], indent=1)[:900])
print('== header keys:', list(h))
print('== victory/defeat:', h.get('victoryIconIndex'), h.get('defeatIconIndex'))
print('== mapLevels:', h.get('mapLevels'))
PY
