"""Read-only published own-state/prerequisite coverage diagnosis; no engine execution."""
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;LAB=Path('/root/heroes3-ai-lab')
TRAIN=LAB/'evaluations/strategic-learned-build-training-01';CAP=LAB/'evaluations/strategic-learned-economy-build-capsule-01';SOURCE=LAB/'src/vcmi-adv'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def main():
    manifest=read(CAP/'build-source-manifest.json');att=read(CAP/'EXECUTION.json')
    assert att['passed'] and att['accepted_binaries_restored'] and not att['rebuild_required']
    inputs={str(CAP/'build-source-manifest.json'):sha(CAP/'build-source-manifest.json'),str(CAP/'EXECUTION.json'):sha(CAP/'EXECUTION.json')};compiled={}
    for relative in ['AI/DirectorAI/CDirectorAI.cpp','lib/callback/CGameInfoCallback.cpp','lib/mapObjects/CGTownInstance.cpp','lib/entities/faction/CTownHandler.cpp','lib/entities/building/CBuilding.h','lib/constants/EntityIdentifiers.h','config/buildingsLibrary.json','config/factions/castle.json']:
        snapshot=CAP/'source-snapshot'/relative
        actual=snapshot if snapshot.exists() else (CAP/'bin'/relative if relative.startswith('config/') else SOURCE/relative)
        assert sha(actual)==manifest[relative]['sha256'],relative
        if snapshot.exists():assert att['candidate_artifacts']['source-snapshot/'+relative]==sha(actual)
        if relative.startswith('config/'):assert att['candidate_artifacts']['bin/'+relative]==sha(actual)
        compiled[relative]=dict(path=str(actual),sha256=sha(actual));inputs[str(actual)]=sha(actual)
    stats=collections.Counter();missing_city=collections.Counter();townhall_missing=collections.Counter();offers=collections.Counter();chosen=collections.Counter();windows=[];cells=[]
    for i in range(8):
        native=TRAIN/f'cell-{i:02d}/native';path=native/'agent/typed-broker.jsonl';inputs[str(path)]=sha(path)
        audit=read(TRAIN/f'cell-{i:02d}/raw-audit/AUDIT.json');assert audit['whole_game_valid'] and audit['raw_sha256']['agent/typed-broker.jsonl']==sha(path)
        inputs[str(TRAIN/f'cell-{i:02d}/raw-audit/AUDIT.json')]=sha(TRAIN/f'cell-{i:02d}/raw-audit/AUDIT.json')
        per_cell=collections.Counter()
        for proposal in [json.loads(line) for line in path.read_text().splitlines()]:
            q=proposal['request'];rid=q['request_id'];raw=native/f'agent/request-{rid:08d}.json'
            assert sha(raw)==proposal['request_sha256'] and read(raw)==q
            stats['states']+=1;per_cell['states']+=1
            selected=q['candidates'][proposal['response']['selected_index']]
            if selected['op']=='build':chosen[selected['building_id']]+=1
            builds=[c for c in q['candidates'] if c['op']=='build']
            for c in builds:stats['legal_build_candidates']+=1;stats['category_'+c['category']]+=1;offers[c['building_id']]+=1
            if not q['economy_window_open']:continue
            stats['build_windows']+=1;per_cell['build_windows']+=1
            stats['windows_with_legal_build']+=bool(builds)
            for town in q['own_towns']:
                assert town['faction_id']==0
                ids=set(town['buildings']);stats['own_town_windows']+=1;stats['built_today_zero']+=town['built_today']==0
                city_missing=tuple(b for b in (0,14,16) if b not in ids);missing_city[city_missing]+=1
                if 11 not in ids:townhall_missing[tuple(b for b in (10,5) if b not in ids)]+=1
                stats['town_hall_already_present']+=11 in ids;stats['city_hall_already_present']+=12 in ids;stats['capitol_already_present']+=13 in ids
                def counts(targets,name):
                    for bid in targets:
                        if bid not in ids:
                            stats[name+'_missing_'+str(bid)]+=1
                            stats[name+'_offered_'+str(bid)]+=any(c['town_id']==town['town_id'] and c['building_id']==bid for c in builds)
                counts((0,14,16),'city_prerequisite')
                windows.append(dict(cell=i,request_id=rid,request_sha256=proposal['request_sha256'],day=q['day'],own_turn=q['own_turn'],
                    town_id=town['town_id'],faction_id=town['faction_id'],built_today=town['built_today'],buildings=town['buildings'],resources=q['resources'],
                    town_hall_present=11 in ids,town_hall_missing_direct_prerequisites=[b for b in (10,5) if b not in ids],
                    city_hall_missing_direct_prerequisites=[b for b in (11,0,14,16) if b not in ids],
                    capitol_missing_direct_prerequisites=[b for b in (12,9) if b not in ids],
                    offered_building_ids=[c['building_id'] for c in builds if c['town_id']==town['town_id']]))
        cells.append(dict(cell=i,counts=dict(per_cell)))
    assert stats['states']==3000 and stats['build_windows']==421 and stats['windows_with_legal_build']==400 and stats['legal_build_candidates']==1473 and stats['category_income']==0,stats
    assert stats['own_town_windows']==430 and stats['built_today_zero']==430
    assert all(w['city_hall_missing_direct_prerequisites'] and w['capitol_missing_direct_prerequisites'] for w in windows)
    assert all(w['town_hall_present'] or w['town_hall_missing_direct_prerequisites'] for w in windows)
    assert set(townhall_missing)=={(5,)} and sum(townhall_missing.values())==20
    assert all(sha(path)==value for path,value in inputs.items())
    result=dict(passed=True,statistics=dict(stats),cells=cells,
        city_missing_mage_market_blacksmith={str(k):v for k,v in missing_city.items()},
        town_hall_absent_missing_direct_prerequisites={str(k):v for k,v in townhall_missing.items()},
        offered_building_ids={str(k):v for k,v in offers.items()},selected_building_ids={str(k):v for k,v in chosen.items()},
        compiled_source_and_config=compiled,input_sha256=inputs,native_runs=0,gpu_runs=0,optimizer_steps=0,
        limits=['No actual canBuildStructure enum was logged for omitted candidates; report proves visible prerequisite/already-built exclusions, not an engine replay.',
                'Forbidden-building flags and fully resolved legacy prices were not logged in policy requests; no hidden map/native-save state was read.',
                'More exploration may select already-offered prerequisites and unlock income on later windows; no guaranteed unlock or strength improvement follows.'])
    write(HERE/'REPORT.json',result);write(HERE/'TOWN_WINDOWS.json',windows)
    print(json.dumps(dict(passed=True,statistics=dict(stats),missing_city=result['city_missing_mage_market_blacksmith'],townhall_missing=result['town_hall_absent_missing_direct_prerequisites'],offers=result['offered_building_ids'],selected=result['selected_building_ids']),indent=2))
if __name__=='__main__':main()
