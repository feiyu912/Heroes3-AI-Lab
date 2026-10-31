"""New non-training fixtures: default one counter vs royal-griffin unlimited.

No change to old runtime/maps. New worker maps root links these separately.
"""
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    here = Path(__file__).resolve().parent
    root = Path('/root/heroes3-ai-lab-events-v3/data/vcmi/Maps/events-v3-probes')
    root.mkdir(parents=True, exist_ok=True)
    source_path = Path('/root/heroes3-ai-lab-events-v2/src/gym/maps/gym/ml-mini.vmap')
    cases=[]
    for target, amount in [('swordsman',40), ('royalGriffin',30)]:
        own=[dict(type='core:pikeman',amount=n) for n in [1,1,1,1,1,1,160]]
        enemy=[dict(type='core:'+target,amount=amount)]+[{} for _ in range(6)]
        path=root/(target+'.vmap')
        assert not path.exists(), 'Never overwrite a frozen fixture'
        with zipfile.ZipFile(source_path) as src, zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as dest:
            for name in src.namelist():
                content=src.read(name)
                if name=='objects.json':
                    objects=json.loads(content)
                    for obj in objects.values():
                        if obj.get('type')=='hero':
                            obj['options'].update(experience=0,
                               primarySkills=dict(attack=0,defence=0,knowledge=0,spellpower=0),
                               secondarySkills=[],spellBook=['preset'],
                               army=own if obj['options']['owner']=='red' else enemy)
                    content=json.dumps(objects).encode()
                dest.writestr(name,content)
        cases.append(dict(id='retaliation-probe-'+target, tactic_id='retaliation-mechanism-probe',
                          split='engineering-probe-not-test', map='events-v3-probes/'+path.name,
                          map_path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          armies=[own,enemy], tight_formation_chance=100,
                          subject_creature=target, expected_rule='one per round' if target=='swordsman' else 'unlimited',
                          human_demonstration=False))
    (here/'retaliation-probes.json').write_text(json.dumps(cases,indent=2))
    print('Created 2 isolated minimal mechanism fixtures; no test/certification claims')


if __name__=='__main__':
    main()
