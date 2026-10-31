#!/usr/bin/env bash
cd / && /root/heroes3-ai-lab/venv/bin/python - <<'PY'
import json, zipfile
p = '/root/heroes3-ai-lab/data/vcmi/Maps/lab/diverse-192.vmap'
with zipfile.ZipFile(p) as z:
    h = json.loads(z.read('header.json'))
    o = json.loads(z.read('objects.json'))
    t = json.loads(z.read('surface_terrain.json'))
print('players:', json.dumps(h['players'], indent=1)[:500])
print('objects:')
for k, v in o.items():
    print(' ', k, v.get('type'), 'pos', v.get('pos'), 'opts', list((v.get('options') or {}).keys())[:6])
print('terrain dims:', len(t), 'x', len(t[0]) if t else 0)
print('terrain sample:', t[0][:8])
PY
