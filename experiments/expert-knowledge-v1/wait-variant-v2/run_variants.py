"""Training-only speed-14 WAIT variants. Does not mutate parent experiment."""
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
spec = importlib.util.spec_from_file_location('source_wait', PARENT/'reconstruct_wait.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.HERE = HERE


def generate():
    cases=[]
    for index, counts in enumerate([(4,80),(6,100),(8,120),(10,140)]):
        for role in ['attacker','defender']:
            fast=[dict(type='core:ghostDragon',amount=counts[0])]+[{} for _ in range(6)]
            slow=[dict(type='core:walkingDead',amount=counts[1])]+[{} for _ in range(6)]
            armies=[fast,slow] if role=='attacker' else [slow,fast]
            name=f'lab/hallas-wait-ghost-v2-{index}-{role}.vmap'
            path=base.ROOT/'data/vcmi/Maps'/name
            with zipfile.ZipFile(base.ROOT/'src/gym/maps/gym/ml-mini.vmap') as source, zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as target:
                for entry in source.namelist():
                    content=source.read(entry)
                    if entry=='objects.json':
                        objects=json.loads(content)
                        for obj in objects.values():
                            if obj.get('type')=='hero':
                                side=int(obj['options']['owner']!='red')
                                obj['options'].update(experience=0,primarySkills=dict(attack=0,defence=0,knowledge=0,spellpower=0),
                                    secondarySkills=[],spellBook=['preset'],army=armies[side])
                        content=json.dumps(objects).encode()
                    target.writestr(entry,content)
            cases.append(dict(id=f'hallas-wait-ghost-v2-{index}-{role}',map=name,role=role,armies=armies,index=index,
                split='train',source_case='hallas-2001-wait-cross-round-action-window',sha256=base.digest(path),
                reconstruction='Lab speed-14 flying undead versus speed-3 undead; not historical human state',
                side_effects='Ghost Dragon aging is not disabled; may affect causal attribution. No dragon breath ability claimed.',
                morale_control='Both stacks undead, avoiding positive morale. Verify actual order.'))
    base.atomic_json(HERE/'source-wait-scenarios.json',cases)
    return cases


def main():
    HERE.mkdir(parents=True,exist_ok=True)
    if not (HERE/'source_wait_case.json').exists():
        shutil.copy2(PARENT/'source_wait_case.json',HERE/'source_wait_case.json')
    frozen={str(path):base.digest(path) for path in [Path(__file__),PARENT/'reconstruct_wait.py',HERE/'source_wait_case.json']}
    base.atomic_json(HERE/'wrapper-provenance.json',dict(files=frozen,
        scope='Train variants only; no test/development outcomes inspected',
        control='Identical counts/map/seed/opponent; only first own decision WAIT versus greedy',
        interpretation='A same-seed advantage is a paired observation, not proof aging and random attack outcomes are causally isolated'))
    cases=json.loads((HERE/'source-wait-scenarios.json').read_text()) if (HERE/'source-wait-scenarios.json').exists() else generate()
    results=[]
    bc=[]
    for case in cases:
        pair=[base.episode(case,wait) for wait in [True,False]]
        normal=all(p['terminated'] and not p['truncated'] and p['terminal_outcome']['result_type']==0 for p in pair)
        benefit=bool(normal and pair[0]['cross_round_window_verified'] and pair[0]['success'] and
            (not pair[1]['success'] or pair[0]['permanent_units_lost']<pair[1]['permanent_units_lost']))
        row=dict(case=case['id'],split='train',normal_pair=normal,wait_success=pair[0]['success'],control_success=pair[1]['success'],
            window_verified=pair[0]['cross_round_window_verified'],wait_loss=pair[0]['permanent_units_lost'],
            control_loss=pair[1]['permanent_units_lost'],benefit_verified=benefit,
            first_followup_action_type=pair[0]['decisions'][1]['action_type'] if len(pair[0]['decisions'])>1 else None,
            possible_confound='Undead avoids positive morale; Ghost Dragon aging and stochastic damage remain possible')
        results.append(row)
        if benefit:
            sample=dict(pair[0]['decisions'][0])
            sample.update(split='train',label_origin='Lab execution of source waiting principle, not human replay',
                label_gate='Measured paired full-battle benefit with real legal WAIT and cross-round timing',
                paired_result=row,source_file=str(HERE/'source_wait_case.json'),
                requires_independent_generalization=True,aging_causal_confound_not_isolated=True)
            bc.append(sample)
        base.atomic_json(HERE/'wait-train-comparison.json',dict(results=results,benefit_cases=sum(r['benefit_verified'] for r in results),
            source_human_replay_obtained=False,source_claim_verified=all(r['window_verified'] for r in results),
            full_event_level_aging_trace=False,provenance=frozen))
        (HERE/'candidate-bc-train.jsonl').write_text(''.join(json.dumps(s)+'\n' for s in bc))
        print(json.dumps(row),flush=True)
    assert all(base.digest(path)==value for path,value in frozen.items())


if __name__=='__main__':
    main()
