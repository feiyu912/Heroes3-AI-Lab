"""Fresh exact-strength mirror suite, kept outside continued training and selection."""
from pathlib import Path
import copy
import hashlib
import json
import numpy as np
import zipfile

root=Path('/root/heroes3-ai-lab')
source=root/'src/gym/maps/gym/ml-mini.vmap'
pools=[['pikeman','archer','griffin'],['centaur','woodElf','pegasus'],['swordsman','monk','cavalier'],
       ['dwarf','woodElf','unicorn'],['pikeman','monk','pegasus'],['dendroidGuard','archer','griffin'],
       ['halberdier','marksman','royalGriffin'],['centaurCaptain','grandElf','silverPegasus']]
rng=np.random.default_rng(2026101501)
cases=[]
for i in range(32):
    amounts=rng.integers([9,5,3],[75,50,30]).tolist()
    slots=sorted(rng.choice(7,3,replace=False).tolist())
    army=[{} for _ in range(7)]
    for slot,type_,amount in zip(slots,pools[i%8],amounts):
        army[slot]=dict(type='core:'+type_,amount=amount)
    # Both sides exactly the same strength and deployment, no troop advantage.
    armies=[army,copy.deepcopy(army)]
    name=f'lab/challenge-mirror-{i:02d}.vmap';target=root/'data/vcmi/Maps'/name
    with zipfile.ZipFile(source) as src,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as dst:
        for entry in src.namelist():
            data=src.read(entry)
            if entry=='objects.json':
                objects=json.loads(data)
                for obj in objects.values():
                    if obj.get('type')=='hero':
                        side=int(obj['options']['owner']!='red')
                        obj['options'].update(experience=0,primarySkills=dict(attack=0,defence=0,knowledge=0,spellpower=0),
                            secondarySkills=[],spellBook=['preset'],army=armies[side])
                data=json.dumps(objects).encode()
            dst.writestr(entry,data)
    cases.append(dict(id=f'challenge-mirror-{i:02d}',map=name,split='challenge-test',armies=armies,
                      sha256=hashlib.sha256(target.read_bytes()).hexdigest(),scope='32 fresh exact mirror three-stack armies; two upgraded compositions unseen in training; no active magic'))
path=Path('/mnt/g/Heroes3-AI-Lab/research/challenge-holdout.json')
path.write_text(json.dumps(cases,indent=2));print('Created',len(cases),'fresh holdout maps')
