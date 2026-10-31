"""Predeclared small multi-stack reconstruction of Hallas' gang-up warning."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('variant_v2',HERE.parent/'wait-variant-v2/run_variants.py')
variant=importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant)
base=variant.base


def generate():
    cases=[]
    for index,(fast_count,slow_count) in enumerate([(4,25),(6,35)]):
        for role in ['attacker','defender']:
            fast=[dict(type='core:ghostDragon',amount=fast_count)]+[{} for _ in range(6)]
            slow=[{},{}]+[dict(type='core:walkingDead',amount=slow_count) for _ in range(3)]+[{},{}]
            armies=[fast,slow] if role=='attacker' else [slow,fast]
            name=f'lab/hallas-wait-multi-v3-{index}-{role}.vmap'
            path=base.ROOT/'data/vcmi/Maps'/name
            with zipfile.ZipFile(base.ROOT/'src/gym/maps/gym/ml-mini.vmap') as source,zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as target:
                for entry in source.namelist():
                    content=source.read(entry)
                    if entry=='objects.json':
                        objects=json.loads(content)
                        for obj in objects.values():
                            if obj.get('type')=='hero':
                                side=int(obj['options']['owner']!='red')
                                obj['options'].update(experience=0,primarySkills=dict(attack=0,defence=0,knowledge=0,spellpower=0),secondarySkills=[],spellBook=['preset'],army=armies[side])
                        content=json.dumps(objects).encode()
                    target.writestr(entry,content)
            cases.append(dict(id=f'hallas-wait-multi-v3-{index}-{role}',map=name,role=role,armies=armies,index=20+index,split='train',
                source_case='hallas-2001-wait-cross-round-action-window',sha256=base.digest(path),
                reconstruction='One fast flyer versus three slower stacks; lab-generated counts/positions, not human replay',
                source_locator='Hallas page5 Waiting to attack final paragraph: flying troops and gang-up risk',
                side_effects='Ghost Dragon aging active; no breath ability claimed; random combat effects not isolated',
                morale_control='All units undead; actual action order must be checked'))
    base.atomic_json(HERE/'source-wait-scenarios.json',cases)
    base.atomic_json(HERE/'preregistered-design.json',dict(
        parameter_groups=[[4,25,25,25],[6,35,35,35]],roles=['attacker','defender'],split='train',
        slow_slots=[2,3,4],seed_indices=[20,21],source='hallas2001',
        reason='One-on-one controls permit additional fast-stack retaliations; source specifically warns of multiple enemies attacking an isolated flyer',
        selection='Fixed before observing any v3 outcomes; no development/test battle outcomes inspected',
        source_script_sha256=base.digest(Path(__file__)),scenario_manifest_sha256=base.digest(HERE/'source-wait-scenarios.json')))
    return cases


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    HERE.mkdir(parents=True,exist_ok=True)
    if not (HERE/'source_wait_case.json').exists():
        shutil.copy2(HERE.parent/'source_wait_case.json',HERE/'source_wait_case.json')
    if not (HERE/'source-wait-scenarios.json').exists():
        generate()
    if args.run:
        base.atomic_json(HERE/'outer-wrapper-provenance.json',dict(files={str(p):base.digest(p) for p in [Path(__file__),HERE.parent/'wait-variant-v2/run_variants.py',HERE/'source_wait_case.json',HERE/'source-wait-scenarios.json']}))
        variant.HERE=HERE
        base.HERE=HERE
        variant.main()
    else:
        print('Generated/frozen four training-only maps; no battles executed')
