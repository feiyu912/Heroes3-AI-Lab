"""Broaden ordinary mirror battle training without using final test results."""
from pathlib import Path
import copy
import hashlib
import json
import numpy as np
import zipfile

root=Path('/root/heroes3-ai-lab');r=Path('/mnt/g/Heroes3-AI-Lab/research')
source=root/'src/gym/maps/gym/ml-mini.vmap'
pools=[['pikeman','archer','griffin'],['centaur','woodElf','pegasus'],
       ['swordsman','monk','cavalier'],['dwarf','woodElf','unicorn'],
       ['pikeman','monk','pegasus'],['dendroidGuard','archer','griffin']]
rng=np.random.default_rng(2026101502)
fingerprint=lambda armies:json.dumps(armies,sort_keys=True,separators=(',',':'))
excluded=set()
for file in ['scenarios-v2.json','challenge-holdout.json']:
    excluded.update(fingerprint(case['armies']) for case in json.loads((r/file).read_text()))
cases=[]
for i in range(240):
    split='train' if i<192 else 'development'
    while True:
        amounts=rng.integers([5,4,2],[100,80,55]).tolist()
        slots=sorted(rng.choice(7,3,replace=False).tolist())
        types=[pools[i%6][j] for j in rng.permutation(3)]
        army=[{} for _ in range(7)]
        for slot,name,count in zip(slots,types,amounts):army[slot]=dict(type='core:'+name,amount=count)
        armies=[army,copy.deepcopy(army)];key=fingerprint(armies)
        if key not in excluded:excluded.add(key);break
    name=f'lab/diverse-{i:03d}.vmap';target=root/'data/vcmi/Maps'/name
    with zipfile.ZipFile(source) as src,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as dst:
        for entry in src.namelist():
            content=src.read(entry)
            if entry=='objects.json':
                objects=json.loads(content)
                for obj in objects.values():
                    if obj.get('type')=='hero':
                        side=int(obj['options']['owner']!='red')
                        obj['options'].update(experience=0,primarySkills=dict(attack=0,defence=0,knowledge=0,spellpower=0),
                            secondarySkills=[],spellBook=['preset'],army=armies[side])
                content=json.dumps(objects).encode()
            dst.writestr(entry,content)
    cases.append(dict(id=f'diverse-{i:03d}',map=name,split=split,armies=armies,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),scope='Exact strength and deployment mirror; six base compositions; varied troop counts, slots and creature ordering'))
(r/'diverse-curriculum.json').write_text(json.dumps(cases,indent=2))
(r/'diverse-curriculum-audit.json').write_text(json.dumps(dict(train_cases=192,development_cases=48,
    all_exact_mirrors=all(c['armies'][0]==c['armies'][1] for c in cases),
    no_exact_duplicates_with_prior_suites=True,excluded_final_suite_for_dedup_only=True,
    final_results_not_used=True,seed=2026101502),indent=2))
print('Created 192 varied training armies and 48 development armies; final test remains separate')
