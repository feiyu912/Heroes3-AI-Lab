#!/usr/bin/env bash
cd / && /root/heroes3-ai-lab/venv/bin/python - <<'PY'
import json, zipfile
from pathlib import Path
from collections import Counter

roots = [Path('/root/heroes3-ai-lab/data/vcmi/Maps')]
stats = Counter()
examples = {}
for root in roots:
    for p in root.rglob('*.vmap'):
        try:
            with zipfile.ZipFile(p) as z:
                h = json.loads(z.read('header.json'))
        except Exception as e:
            stats['unreadable'] += 1
            continue
        players = h.get('players') or {}
        types = set()
        for pl in players.values():
            for hero in (pl.get('heroes') or {}).values():
                types.add(hero.get('type', ''))
        key = 'ml-heroes' if any(t.startswith('ml:') for t in types) else 'core-heroes'
        stats[key] += 1
        examples.setdefault(key, []).append(str(p))
print(dict(stats))
for k, v in examples.items():
    print(k, 'examples:', v[:5])
PY
