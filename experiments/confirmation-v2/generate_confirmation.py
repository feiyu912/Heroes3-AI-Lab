"""CPU-only fresh mirror fixtures. Existing files are verified, never overwritten."""
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np

HERE=Path(__file__).resolve().parent
LAB=HERE.parents[1]
RUNTIME=Path('/root/heroes3-ai-lab')
TEMPLATE=RUNTIME/'src/gym/maps/gym/ml-mini.vmap'
HEROES=RUNTIME/'data/vcmi/Mods/ML/Content/heroes.json'
SEED=2026101601
POOLS=[['pikeman','archer','griffin'],['centaur','woodElf','pegasus'],['swordsman','monk','cavalier'],
       ['dwarf','woodElf','unicorn'],['pikeman','monk','pegasus'],['dendroidGuard','archer','griffin'],
       ['halberdier','marksman','royalGriffin'],['centaurCaptain','grandElf','silverPegasus']]
KNOWN=[LAB/'research'/name for name in ['scenarios-v1.json','scenarios-v2.json','diverse-curriculum.json','challenge-holdout.json']]
KNOWN += [LAB/'experiments/human-tactics-v1/scenarios.json',
    LAB/'experiments/expert-knowledge-v1/source-wait-scenarios.json',
    LAB/'experiments/expert-knowledge-v1/wait-variant-v2/source-wait-scenarios.json',
    LAB/'experiments/expert-knowledge-v1/wait-variant-v2/heldout-scenarios.json',
    LAB/'experiments/expert-knowledge-v1/wait-variant-v2/all-source-wait-scenarios.json',
    LAB/'experiments/expert-knowledge-v1/wait-variant-v3/source-wait-scenarios.json',
    Path('/mnt/g/Heroes3-AI-Lab-worktrees/human-expert-learning-v1/tools/human_expert/evidence/scenarios.json'),
    Path('/mnt/g/Heroes3-AI-Lab-worktrees/human-expert-learning-v1/tools/human_expert/runs/pilot-04/scenarios.json')]


def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def strength(army):
    return tuple(sorted((unit['type'],int(unit['amount'])) for unit in army if unit))
def write_or_verify(path,data):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        assert path.read_bytes()==data,'Refuse to overwrite differing existing file: '+str(path)
    else:
        with path.open('xb') as stream:stream.write(data)


def main():
    source_bytes=TEMPLATE.read_bytes()
    heroes_bytes=HEROES.read_bytes();hero_defs=json.loads(heroes_bytes)
    manifest_hashes={};old_strengths=set();old_slot_armies=set();old_cases=0
    for path in KNOWN:
        assert path.exists(),'Required exclusion manifest missing: '+str(path)
        payload=path.read_bytes();manifest_hashes[str(path)]=sha(payload)
        cases=json.loads(payload);assert isinstance(cases,list)
        for case in cases:
            assert isinstance(case.get('armies'),list) and len(case['armies'])==2
            old_cases+=1
            for army in case['armies']:
                old_strengths.add(strength(army));old_slot_armies.add(sha(encoded(army)))
    rng=np.random.default_rng(SEED)
    cases=[];seen=set();rejections=[];map_audits=[]
    source=zipfile.ZipFile(io.BytesIO(source_bytes))
    original_objects=json.loads(source.read('objects.json'))
    for i in range(32):
        while True:
            amounts=rng.integers([9,5,3],[75,50,30]).tolist()
            slots=sorted(rng.choice(7,3,replace=False).tolist())
            army=[{} for _ in range(7)]
            for slot,name,amount in zip(slots,POOLS[i%8],amounts):army[slot]=dict(type='core:'+name,amount=amount)
            key=strength(army)
            if key in old_strengths or key in seen:
                rejections.append(dict(case_index=i,reason='same non-positional stack composition as known army' if key in old_strengths else 'duplicate new army',army=army))
                continue
            seen.add(key);break
        armies=[army,copy.deepcopy(army)]
        objects=copy.deepcopy(original_objects);hero_count=0
        for obj in objects.values():
            if obj.get('type')!='hero':continue
            hero_count+=1;options=obj['options'];side=int(options['owner']!='red')
            assert options['owner'] in ['red','blue']
            options.update(experience=0,primarySkills=dict(attack=0,defence=0,knowledge=0,spellpower=0),secondarySkills=[],spellBook=['preset'],army=copy.deepcopy(armies[side]))
            assert not options.get('artifacts'), 'Template unexpectedly contains equipped artifacts'
            definition=hero_defs[options['type'].split(':',1)[1]]
            assert definition['skills']==[] and definition['spellbook']==[] and definition['specialty']=={}
        assert hero_count==4
        changed=json.dumps(objects,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        memory=io.BytesIO()
        with zipfile.ZipFile(memory,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as target:
            for entry in source.infolist():
                info=zipfile.ZipInfo(entry.filename,date_time=(2026,10,16,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED;info.create_system=entry.create_system;info.external_attr=entry.external_attr
                data=changed if entry.filename=='objects.json' else source.read(entry.filename)
                target.writestr(info,data,compresslevel=6)
        payload=memory.getvalue()
        name=f'lab/confirmation-v2-{i:02d}.vmap'
        path=RUNTIME/'data/vcmi/Maps'/name
        assert path.parent.resolve()==(RUNTIME/'data/vcmi/Maps/lab').resolve()
        write_or_verify(path,payload)
        with zipfile.ZipFile(path) as readback:
            assert readback.namelist()==source.namelist()
            loaded=json.loads(readback.read('objects.json'));actual_heroes=[obj for obj in loaded.values() if obj.get('type')=='hero']
            assert len(actual_heroes)==4
            for obj in actual_heroes:
                o=obj['options'];side=int(o['owner']!='red')
                assert o['army']==armies[side] and o['primarySkills']==dict(attack=0,defence=0,knowledge=0,spellpower=0)
                assert o['experience']==0 and o['secondarySkills']==[] and o['spellBook']==['preset'] and not o.get('artifacts')
            unchanged={entry:sha(readback.read(entry)) for entry in readback.namelist() if entry!='objects.json'}
            assert all(readback.read(entry)==source.read(entry) for entry in unchanged)
        assert armies[0]==armies[1] and len([u for u in army if u])==3
        assert strength(army) not in old_strengths and sha(encoded(army)) not in old_slot_armies
        case=dict(id=f'confirmation-v2-{i:02d}',map=name,split='confirmation-test-v2',armies=armies,
            sha256=sha(payload),composition_index=i%8,variant_index=i//8,random_obstacles=0,
            scope='Fresh counts and slots in eight previously defined creature compositions; exact mirror, no active hero magic; not unseen-creature generalization')
        cases.append(case)
        map_audits.append(dict(case=case['id'],path=str(path),sha256=sha(path.read_bytes()),objects_sha256=sha(changed),hero_count=4,
            exact_armies_and_slots_mirror=True,zero_hero_primary_secondary_experience=True,no_artifacts_or_preset_spells=True,
            zip_readback_passed=True,non_objects_entries_identical_to_template=unchanged))
    source.close()
    case_bytes=encoded(cases)
    plan=dict(schema='heroes3-confirmation-v2-plan',fixture_seed=SEED,battle_seed_base=SEED,
        battle_seed_rule='battle_seed_base + case_index*100 + seed_index (seed_index 0..7)',
        cases=32,roles=['attacker','defender'],seeds_per_case_role=8,battles_per_opponent=512,
        opponents=['native BattleAI','native CPU original public MMAI ONNX'],candidate_model=None,candidate_model_selected=False,
        model_final_freeze_created=False,fixture_definition_sha256=sha(case_bytes),
        selection_rule='Select on existing development evidence, then freeze one candidate before reading any v2 outcome; never select model or tune training on this confirmation suite',
        unchanged_objective='BattleAI win rate at least 95%; author-model advantage judged by existing scenario-cluster uncertainty criteria, no relaxed threshold',
        after_failure='Viewed v2 outcomes become diagnostics; any further training requires a newly declared fresh confirmation suite',
        environment=dict(no_active_hero_magic=True,random_heroes=0,random_obstacles=0,town_chance=0,warmachine_chance=0,mana_min=0,mana_max=0,random_armies=False),
        native_execution_performed=False,results_read=False,results_exist_created_by_generator=False,
        unknowns=['Native execution compatibility has not been tested','Public-model pretraining exposure to these creatures is unknown','Same template and eight known compositions; no new-creature or new-source generalization claim','Morale, luck, terrain and creature abilities follow the preserved engine/template, not newly controlled event-level experiments'])
    audit=dict(schema='heroes3-confirmation-v2-fixture-audit',status='static_fixture_checks_passed_not_native_executed',
        generator_sha256=sha(Path(__file__).read_bytes()),reference_generator=dict(path=str(LAB/'research/make-challenge-holdout.py'),sha256=sha((LAB/'research/make-challenge-holdout.py').read_bytes())),
        template=dict(path=str(TEMPLATE),sha256=sha(source_bytes)),hero_definitions=dict(path=str(HEROES),sha256=sha(heroes_bytes),used_ids=['hero_0','hero_1','hero_2','hero_3'],skills_specialty_spells_empty=True),
        numpy_version=np.__version__,fixture_seed=SEED,rng='numpy default_rng PCG64',amount_lower_inclusive=[9,5,3],amount_upper_exclusive=[75,50,30],
        pools=POOLS,composition_counts={str(pool):sum(c['composition_index']==pool for c in cases) for pool in range(8)},
        exclusion_manifest_sha256=manifest_hashes,exclusion_records_with_manifest_repetitions=old_cases,excluded_distinct_nonpositional_armies=len(old_strengths),
        candidate_rejections=rejections,new_distinct_nonpositional_armies=len(seen),known_army_overlap=0,new_internal_duplicate_armies=0,
        duplicate_rule='Reject candidate if its sorted creature/type-and-stack-count multiset occurs on either side of any listed fixture, ignoring slot positions; also reject duplicate new composition/counts',
        scenarios_sha256=sha(case_bytes),maps=map_audits,all_32_zip_readbacks_passed=True,all_128_hero_records_neutral=True,
        original_rules_entries_preserved=True,native_execution_performed=False,results_read=False,candidate_model_selected=False,
        actual_model_freeze_created=False,non_overwrite_policy='Exclusive create if absent; if present require exact bytes and leave untouched',
        unknowns=plan['unknowns'])
    for name,value in [('scenarios.json',cases),('plan.json',plan),('fixture-audit.json',audit)]:write_or_verify(HERE/name,encoded(value))
    assert TEMPLATE.read_bytes()==source_bytes and HEROES.read_bytes()==heroes_bytes
    for path,h in manifest_hashes.items():assert sha(Path(path).read_bytes())==h
    print(json.dumps(dict(status=audit['status'],maps=32,heroes=128,known_overlap=0,manifest_count=len(KNOWN),existing_records=old_cases,rejections=len(rejections),scenarios_sha256=sha(case_bytes),native_games=0,model_selected=False)))


if __name__=='__main__':main()
