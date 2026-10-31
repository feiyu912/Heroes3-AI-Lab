"""Shared native quiescence boundary; preserve every failed prior pair."""
from pathlib import Path
import difflib,hashlib,json,shutil
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'multihero-scheduler-garrison-v3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,(a[:80],s.count(a))
    return s.replace(a,b,1)
def main():
    (HERE/'candidates').mkdir(exist_ok=False)
    for arm in ('baseline','filtered'):
        cpp=(OLD/'candidates'/arm/'CDirectorAI.cpp').read_text()
        h=(OLD/'candidates'/arm/'CDirectorAI.h').read_text()
        original=cpp
        h=once(h,'bool setupGarrisonControl();','bool setupGarrisonControl();\n    bool schedulerHeld = false;\n    std::map<int, int3> schedulerTurnStart;')
        cpp=once(cpp,'\t++ownTurns;','''    schedulerTurnStart.clear();
    for(const auto * hero : cb->getHeroesInfo())
        if(hero->getOwner() == playerID && (hero->id.getNum() == 0 || hero->id.getNum() == 2))
            schedulerTurnStart[hero->id.getNum()] = hero->visitablePos();
\t++ownTurns;''')
        cpp=once(cpp,'    if(!garrisonSetupDone)', '''    if(schedulerHeld) return;
    if(ownTurns == 2 && schedulerTurnStart.size() == 2)
    {
        const auto * a = cb->getHero(ObjectInstanceID(0));
        const auto * b = cb->getHero(ObjectInstanceID(2));
        if(a && b && a->visitablePos() != schedulerTurnStart.at(0) &&
           b->visitablePos() != schedulerTurnStart.at(2))
        {
            schedulerHeld = true;
            traceState("scheduler_quiescent_boundary");
            probeEvent("scheduler_quiescent_boundary");
            return;
        }
    }
    if(!garrisonSetupDone)''')
        dest=HERE/'candidates'/arm;dest.mkdir()
        (dest/'CDirectorAI.cpp').write_text(cpp);(dest/'CDirectorAI.h').write_text(h)
        (HERE/f'boundary-{arm}.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),cpp.splitlines(True))))
    for name in ('capsule_support.py','audit_legacy.py','audit_scheduler.py','build_scheduler.py','derive.py','DERIVATION.json','prepare_runner.py','fixture-02.json','fixture-03.vmap','FIXTURE_DERIVATION.json'):
        shutil.copy2(OLD/name,HERE/name)
    runner=(OLD/'run_scheduler.py').read_text()
    runner=once(runner,'    return True\n\n\n','    return any(r.get("event")=="scheduler_quiescent_boundary" for r in rows)\n\n\n')
    runner=runner.replace('HERE / "prepare.py", HERE / "FIXTURE_DERIVATION.json",','HERE / "prepare.py", HERE / "BOUNDARY_DERIVATION.json", HERE / "FIXTURE_DERIVATION.json",')
    (HERE/'run_scheduler.py').write_text(runner)
    audit=(HERE/'audit_scheduler.py').read_text()
    audit=once(audit,"hero(r,3)['garrisoned'] is True and hero(r,3)['town_id']==ah['town_id'] and",
        "hero(r,3)['garrisoned'] is True and hero(r,3)['owner']==a['player'] and hero(r,3)['town_id']==ah['town_id'] and")
    audit=once(audit,'    selected=[r for r in probe', '''    require('garrison_town_reference_persists',all(
        len([t for t in r['towns'] if t['id']==ah['town_id'] and t['owner']==a['player'] and t['garrison_id']==3 and t['upper_army_id']==3])==1
        for r in post))
    selected=[r for r in probe''')
    audit=once(audit,'    return checks,', '''    boundary=[(i,r) for i,r in enumerate(probe) if r['event']=='scheduler_quiescent_boundary']
    require('one_quiescent_boundary',len(boundary)==1)
    if len(boundary)==1:
        bi,br=boundary[0]
        require('boundary_no_pending_requests',br['pending_move']==0 and br['pending_queries']==0 and br['query_requests']==0 and br['own_turn']==2)
        require('no_action_after_boundary',not any(r['event'] in ('scheduler_selected','move_issued','move_sent','endturn_sent','close_sent','transfer_sent') for r in probe[bi+1:]))
    return checks,''')
    (HERE/'audit_scheduler.py').write_text(audit)
    b=(HERE/'candidates/baseline/CDirectorAI.cpp').read_text();f=(HERE/'candidates/filtered/CDirectorAI.cpp').read_text()
    assert f==once(b,'hero->getOwner() != playerID || blockedHeroes.count(hero->id.getNum())','hero->getOwner() != playerID || hero->isGarrisoned() || blockedHeroes.count(hero->id.getNum())')
    assert (HERE/'candidates/baseline/CDirectorAI.h').read_bytes()==(HERE/'candidates/filtered/CDirectorAI.h').read_bytes()
    record={'map_sha256':sha(HERE/'fixture-03.vmap'),
        'parent_map_sha256':sha(OLD/'fixture-03.vmap'),'fixture_identical':True,
        'common_change':'At original advanceTurn no-pending guard, hold after both mobile heroes actually changed position in own turn2; emit native boundary then no further actions.',
        'single_factor':'Only filtered excludes isGarrisoned from pickHero',
        'candidates':{a:{n:sha(HERE/'candidates'/a/n) for n in ('CDirectorAI.cpp','CDirectorAI.h')} for a in ('baseline','filtered')},
        'native_runs':0,'optimizer_steps':0}
    (HERE/'BOUNDARY_DERIVATION.json').write_text(json.dumps(record,indent=2))
    (HERE/'DERIVATION.json').write_text(json.dumps(record,indent=2))
if __name__=='__main__':main()
