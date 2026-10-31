"""Audit actual mirror maps and neutral hero definitions, without outcome data."""
import hashlib
import json
from pathlib import Path
import zipfile
from lab_io import atomic_json


def main():
    research=Path(__file__).resolve().parent
    data=Path('/root/heroes3-ai-lab/data/vcmi')
    hero_path=data/'Mods/ML/Content/heroes.json'
    definitions=json.loads(hero_path.read_text())
    checksum=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
    records=[];referenced={}
    for filename in ['diverse-curriculum.json','challenge-holdout.json']:
        for case in json.loads((research/filename).read_text()):
            assert case['armies'][0]==case['armies'][1]
            path=data/'Maps'/case['map']
            assert checksum(path)==case['sha256']
            with zipfile.ZipFile(path) as archive:
                objects=json.loads(archive.read('objects.json'))
            heroes=[obj for obj in objects.values() if obj.get('type')=='hero']
            assert len(heroes)==4
            assert {obj['options']['owner'] for obj in heroes}=={'red','blue'}
            for hero in heroes:
                options=hero['options'];side=int(options['owner']=='blue')
                assert options['army']==case['armies'][side]
                assert options['experience']==0 and options['secondarySkills']==[]
                assert options['primarySkills']==dict(attack=0,defence=0,knowledge=0,spellpower=0)
                assert options['spellBook']==['preset'] and not options.get('artifacts')
                assert options['type'].startswith('ml:')
                definition=definitions[options['type'].split(':',1)[1]]
                assert definition['skills']==[] and definition['specialty']=={} and definition['spellbook']==[]
                referenced[options['type']]=definition['class']
            records.append(dict(suite=filename,case=case['id'],sha256=case['sha256'],neutral_heroes=4))
    assert len(set(referenced.values()))==1
    atomic_json(research/'neutral-mirror-fixtures-audit.json',dict(passed=True,checked_maps=len(records),
        hero_definitions_file=str(hero_path),hero_definitions_sha256=checksum(hero_path),referenced_classes=referenced,
        all_armies_and_slots_exact_mirrors=True,all_heroes_same_class=True,
        all_primary_skills_zero=True,no_secondary_skills_or_specialties=True,
        no_artifacts_or_preset_spells=True,final_results_read=False,records=records,
        scope='Static fixture and active ML-mod data audit, not a claim about battle outcomes. Native v15 still has its original 30-round guard; non-normal endings are not wins.'))
    print('Neutral hero and mirror-map audit passed:',len(records),'maps',flush=True)


if __name__=='__main__':main()
