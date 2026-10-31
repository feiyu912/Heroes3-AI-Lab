"""Actual TRAIN schema5 feature identifiability study. No game, optimizer or DEV input."""
import argparse,collections,copy,hashlib,importlib.util,itertools,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;EXP=HERE.parent
sys.path.insert(0,str(EXP/'strategic-learned-free-transfer-policy-v1'))
TRAIN=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-free-transfer-train-01')
CAP=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-economy-build-capsule-02')
SOURCE=Path('/root/heroes3-ai-lab/src/vcmi-adv')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def stable(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def jsonc(path):
    # VCMI config uses comments/trailing commas; strip them outside strings only.
    text=Path(path).read_text();out=[];i=0;quoted=False;escaped=False
    while i<len(text):
        c=text[i]
        if quoted:
            out.append(c)
            if escaped:escaped=False
            elif c=='\\':escaped=True
            elif c=='"':quoted=False
            i+=1;continue
        if c=='"':quoted=True;out.append(c);i+=1;continue
        if text.startswith('//',i):
            end=text.find('\n',i);i=len(text) if end<0 else end;continue
        if text.startswith('/*',i):
            end=text.find('*/',i+2);assert end>=0;i=end+2;continue
        if c==',':
            j=i+1
            while j<len(text) and text[j].isspace():j+=1
            if j<len(text) and text[j] in '}]':i+=1;continue
        out.append(c);i+=1
    return json.loads(''.join(out))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);a=parser.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    encoder=module('_economic_observation_actual_encoder',EXP/'strategic-learned-free-transfer-policy-v1/encoder.py')
    loader=module('_economic_observation_admission',EXP/'strategic-learned-free-transfer-policy-v1/load_admitted.py')
    manifest=json.loads((CAP/'build-source-manifest.json').read_text());att=json.loads((CAP/'EXECUTION.json').read_text())
    assert att['passed'] and att['accepted_binaries_restored'] and not att['rebuild_required']
    inputs={str(CAP/'build-source-manifest.json'):sha(CAP/'build-source-manifest.json'),str(CAP/'EXECUTION.json'):sha(CAP/'EXECUTION.json')}
    paths=[('config/buildingsLibrary.json',CAP/'bin/config/buildingsLibrary.json'),
           ('config/factions/castle.json',CAP/'bin/config/factions/castle.json'),
           ('lib/constants/EntityIdentifiers.h',SOURCE/'lib/constants/EntityIdentifiers.h')]
    source_facts={}
    for rel,path in paths:
        assert sha(path)==manifest[rel]['sha256'];inputs[str(path)]=sha(path)
        target=a.out/'native-source'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(path.read_bytes())
        source_facts[rel]=dict(path=str(path),sha256=sha(path),manifest_verified=True)
    buildings=jsonc(paths[0][1]);castle=jsonc(paths[1][1])
    castle_buildings=castle['castle']['town']['buildings']
    semantics={name:dict(building_id=buildings[name]['id'],shared_definition=buildings[name],castle_definition=castle_buildings.get(name)) for name in ('tavern','marketplace')}
    enum_text=paths[2][1].read_text();enum_lines=enum_text.splitlines()
    excerpts=[]
    for i,line in enumerate(enum_lines):
        if any(name in line for name in ('TAVERN','MARKETPLACE','TOWN_HALL')):excerpts.append(dict(line=i+1,text=line))
    collisions=[];town_changes=[];full_encoded={};actual_input_collisions=[];paircounts=collections.Counter();observed_costs=collections.defaultdict(set)
    rows_checked=0;build_rows=0;request_with_build=0;prototype=None;all_requests=[];rechecked={};build_candidates_by_id=collections.Counter()
    for cell in sorted(TRAIN.glob('cell-*')):
        samples,episodes,report=loader.load(cell/'admitted');assert len(episodes)==1
        inputs[str(cell/'admitted/AUDIT.json')]=sha(cell/'admitted/AUDIT.json')
        raw=json.loads((cell/'raw-audit/AUDIT.json').read_text());plan=json.loads((cell/'native/PLAN.json').read_text())
        for name,h in raw['raw_sha256'].items():
            path=str(cell/'native'/name);assert sha(path)==h;rechecked[path]=h
        for path,h in plan['hashes'].items():
            if path not in rechecked:assert sha(path)==h
            else:assert rechecked[path]==h
            rechecked[path]=h
        previous={}
        for sample in samples:
            q=sample['request'];state,features=encoder.encode(q);rows_checked+=1;all_requests.append((cell.name,q))
            town_by_id={t['town_id']:t for t in q['own_towns']};groups=collections.defaultdict(list);buildidx=[]
            for index,candidate in enumerate(q['candidates']):
                if candidate['op']!='build':continue
                build_rows+=1;buildidx.append(index);build_candidates_by_id[candidate['building_id']]+=1
                groups[tuple(features[index])].append(index)
                if candidate['building_id'] in (5,14):observed_costs[candidate['building_id']].add(tuple(candidate['cost'][r] for r in encoder.RESOURCES))
            request_with_build+=bool(buildidx)
            if buildidx and prototype is None:prototype=copy.deepcopy(q)
            for indices in groups.values():
                if len(indices)<2:continue
                candidates=[q['candidates'][i] for i in indices]
                for x,y in itertools.combinations(candidates,2):
                    key=('same_town' if x['town_id']==y['town_id'] else 'different_town',min(x['building_id'],y['building_id']),max(x['building_id'],y['building_id']))
                    paircounts[key]+=1
                collisions.append(dict(cell=cell.name,request_id=q['request_id'],day=q['day'],own_turn=q['own_turn'],
                    candidate_indices=indices,candidates=candidates,
                    actor_facts=[dict(town_id=c['town_id'],faction_id=town_by_id[c['town_id']]['faction_id'],buildings=town_by_id[c['town_id']]['buildings']) for c in candidates],
                    identical_encoded_row=features[indices[0]],same_town_different_building=any(x['town_id']==y['town_id'] and x['building_id']!=y['building_id'] for x,y in itertools.combinations(candidates,2))))
            for tid,town in town_by_id.items():
                old=previous.get(tid)
                if old and old['town']['buildings']!=town['buildings']:
                    town_changes.append(dict(cell=cell.name,town_id=tid,before_request_id=old['request_id'],after_request_id=q['request_id'],
                        before_buildings=old['town']['buildings'],after_buildings=town['buildings'],
                        full_encoder_equal=old['encoded']==(state,features),
                        scope='Actual successive own-town observations; other visible state/candidate fields may also change, so this alone does not isolate building encoding.'))
                previous[tid]=dict(request_id=q['request_id'],town=copy.deepcopy(town),encoded=(state,features))
            encoded_key=stable([state,features]);facts=[dict(town_id=t['town_id'],faction_id=t['faction_id'],buildings=t['buildings']) for t in q['own_towns']]
            if encoded_key in full_encoded and full_encoded[encoded_key]['facts']!=facts:
                actual_input_collisions.append(dict(first=full_encoded[encoded_key],second=dict(cell=cell.name,request_id=q['request_id'],facts=facts),same_complete_encoded_input=True,
                    scope='Actual requests, possibly different episodes; metadata/raw candidates may differ. Not a causal matched game.'))
            full_encoded.setdefault(encoded_key,dict(cell=cell.name,request_id=q['request_id'],facts=facts))
    assert rows_checked==2089 and prototype is not None
    # Explicit CPU counterexamples: fixed published candidates are not certified
    # legal in the altered town state. This diagnoses discarded inputs only.
    state0,rows0=encoder.encode(prototype);counterexamples=[]
    for field in ('buildings','faction_id'):
        other=copy.deepcopy(prototype);town=other['own_towns'][0];before=copy.deepcopy(town[field])
        if field=='buildings':
            offered={c['building_id'] for c in other['candidates'] if c['op']=='build' and c['town_id']==town['town_id']}
            bid=next(i for i in range(44) if i not in town['buildings'] and i not in offered)
            town['buildings']=sorted(town['buildings']+[bid])
        else:town['faction_id']=(town['faction_id']+1)%9
        state1,rows1=encoder.encode(other);assert state0==state1 and rows0==rows1
        counterexamples.append(dict(field=field,town_id=town['town_id'],before=before,after=town[field],
            complete_encoded_input_identical=True,CPU_constructed_not_native=True,
            altered_candidates_not_native_legality_certified=True))
    same_tavern_market=[c for c in collisions if any(x['building_id']==5 and y['building_id']==14 and x['town_id']==y['town_id'] for x,y in itertools.permutations(c['candidates'],2))]
    assert all(sha(path)==h for path,h in rechecked.items())
    report=dict(passed=True,CPU_only=True,new_native_games=0,GPU_steps=0,optimizer_steps=0,DEV_inputs_used=False,
        actual_TRAIN_requests=rows_checked,requests_with_build_candidates=request_with_build,total_build_candidates=build_rows,
        exact_row_collision_groups=len(collisions),requests_with_collisions=len({(c['cell'],c['request_id']) for c in collisions}),
        same_town_distinct_building_collision_groups=sum(c['same_town_different_building'] for c in collisions),
        same_town_tavern_market_collision_groups=len(same_tavern_market),
        candidate_counts_by_building_id=dict(build_candidates_by_id),
        observed_tavern_market_costs={str(k):[dict(zip(encoder.RESOURCES,v)) for v in sorted(values)] for k,values in observed_costs.items()},
        collision_pair_counts=[dict(relation=k[0],building_ids=list(k[1:]),occurrences=v) for k,v in sorted(paircounts.items())],
        actual_building_state_change_pairs=len(town_changes),actual_change_pairs_with_identical_encoder=sum(c['full_encoder_equal'] for c in town_changes),
        actual_complete_input_collisions_differing_town_facts=len(actual_input_collisions),
        constructed_discarded_input_checks=counterexamples,native_semantics=semantics,enum_excerpts=excerpts,
        native_sources=source_facts,input_sha256=inputs,rechecked_original_raw_source_runtime_inputs=len(rechecked),
        encoder_wrapper_sha256=sha(EXP/'strategic-learned-free-transfer-policy-v1/encoder.py'),
        actual_encoder_sha256=sha(EXP/'strategic-learned-economy-policy-v1/encoder.py'),auditor_sha256=sha(Path(__file__)),
        limitation='Identifiability evidence on this TRAIN set only. It is separate from the q4 return-home branch and does not establish any game outcome cause or an improvement.')
    for name,data in [('AUDIT.json',report),('ROW_COLLISIONS.json',collisions),('ACTUAL_BUILDING_CHANGES.json',town_changes),
        ('ACTUAL_COMPLETE_INPUT_COLLISIONS.json',actual_input_collisions),('RAW_SOURCE_RECHECK.json',rechecked)]:
        (a.out/name).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('collision_pair_counts','native_semantics','native_sources','input_sha256','constructed_discarded_input_checks','candidate_counts_by_building_id')},indent=2))
if __name__=='__main__':main()
