"""Generate preregistered development/test fixtures without running battles."""
import copy
import importlib.util
import json
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('wait_variant',HERE/'run_variants.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
base=module.base

cases=[]
for index,(split,fast_count,slow_count) in enumerate([
    ('development',5,90),('development',7,110),('test',9,130),('test',11,150)],start=4):
    for role in ['attacker','defender']:
        fast=[dict(type='core:ghostDragon',amount=fast_count)]+[{} for _ in range(6)]
        slow=[dict(type='core:walkingDead',amount=slow_count)]+[{} for _ in range(6)]
        armies=[fast,slow] if role=='attacker' else [slow,fast]
        name=f'lab/hallas-wait-ghost-v2-{index}-{role}.vmap'
        path=base.ROOT/'data/vcmi/Maps'/name
        assert not path.exists(),f'Refuse to overwrite holdout {path}'
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
        cases.append(dict(id=f'hallas-wait-ghost-v2-{index}-{role}',map=name,role=role,armies=armies,index=index,split=split,
            source_case='hallas-2001-wait-cross-round-action-window',sha256=base.digest(path),
            reconstruction='Predeclared unobserved holdout; same unit family, novel counts and disjoint seed',
            seed=2026103001+index,side_effects='Ghost Dragon aging remains possible; not disabled',
            morale_control='Both stacks undead; verify actual order'))
base.atomic_json(HERE/'heldout-scenarios.json',cases)
base.atomic_json(HERE/'holdout-freeze.json',dict(
    plan='Parent-requested exact counts fixed before inspecting any variant outcome; no heldout battles run',
    parameter_groups={'development':[[5,90],[7,110]],'test':[[9,130],[11,150]]},
    scenario_manifest_sha256=base.digest(HERE/'heldout-scenarios.json'),
    generator_sha256=base.digest(Path(__file__)),fixture_sha256={case['map']:case['sha256'] for case in cases},
    scope_limit='Same creature matchup and opponent script; not an independent test of broad BattleAI strength'))
print(json.dumps({'generated_holdout_maps':len(cases),'battle_runs':0}))
