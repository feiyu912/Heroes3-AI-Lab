"""Six new exact mirrors, locked train/dev/test before any run."""
import copy
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    here=Path(__file__).resolve().parent
    root=Path('/root/heroes3-ai-lab-events-v3/data/vcmi/Maps/events-v3-probes')
    source=Path('/root/heroes3-ai-lab-events-v2/src/gym/maps/gym/ml-mini.vmap')
    cases=[]
    for index,(main_count,slots,tight) in enumerate([(12,[0,2,5],100),(18,[1,4,6],0),
               (15,[0,3,6],0),(23,[1,2,5],100),(17,[0,4,6],100),(21,[1,3,5],0)]):
        army=[{} for _ in range(7)]
        for slot,typ,n in zip(slots,['pikeman','pikeman','swordsman'],[1,1,main_count]):
            army[slot]=dict(type='core:'+typ,amount=n)
        path=root/f'wait-bait-{index:02d}.vmap'
        assert not path.exists()
        with zipfile.ZipFile(source) as src,zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as dst:
            for name in src.namelist():
                content=src.read(name)
                if name=='objects.json':
                    obj=json.loads(content)
                    for hero in obj.values():
                        if hero.get('type')=='hero':
                            hero['options'].update(experience=0,primarySkills=dict(attack=0,defence=0,knowledge=0,spellpower=0),
                                                   secondarySkills=[],spellBook=['preset'],army=army)
                    content=json.dumps(obj).encode()
                dst.writestr(name,content)
        cases.append(dict(id=f'wait-bait-v1-{index:02d}',tactic_id='wait-bait-ordering',
                          split='train' if index<2 else 'development' if index<4 else 'locked-test',
                          map='events-v3-probes/'+path.name,map_path=str(path),
                          sha256=hashlib.sha256(path.read_bytes()).hexdigest(),armies=[army,copy.deepcopy(army)],
                          tight_formation_chance=tight))
    (here/'scenarios.json').write_text(json.dumps(cases,indent=2))
    print('Frozen 6 new mirrored fixtures: train2/dev2/locked-test2')


if __name__=='__main__':
    main()
