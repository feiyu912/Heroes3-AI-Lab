"""Isolate a real server garrison setup and one scheduler eligibility change."""
import difflib,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'multihero-scheduler-probe-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def once(s,a,b):
    assert s.count(a)==1,(a[:100],s.count(a))
    return s.replace(a,b,1)
def main():
    source=(OLD/'candidates/scheduler/CDirectorAI.cpp').read_text()
    header=(OLD/'candidates/scheduler/CDirectorAI.h').read_text()
    original=source
    header=once(header,'int probeHero = -1;', '''int probeHero = -1;
    bool garrisonSetupPending = false, garrisonSetupDone = false;
    int garrisonSetupRequest = -1, garrisonSetupTown = -1;
    bool setupGarrisonControl();''')
    source=once(source,'\tif(issueEconomy())', '''    if(!garrisonSetupDone)
    {
        if(garrisonSetupPending) return;
        setupGarrisonControl();
        return;
    }
\tif(issueEconomy())''')
    source=once(source,'\tint3 destination(-1, -1, -1);', '''    probeHero = hero->id.getNum();
    traceState("scheduler_selection");
    probeEvent("scheduler_selected");
\tint3 destination(-1, -1, -1);''')
    source=once(source,'void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)\n{', '''void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)
{
    if(const auto * swap = dynamic_cast<const GarrisonHeroSwap *>(pack))
    {
        if(!garrisonSetupPending || garrisonSetupRequest != -1 ||
           swap->tid.getNum() != garrisonSetupTown || pack->player != playerID || requestID < 1)
            throw std::runtime_error("Garrison setup request tuple mismatch");
        garrisonSetupRequest = requestID;
        probeEvent("garrison_setup_sent", requestID);
    }''')
    source=once(source,'void CDirectorAI::requestRealized(PackageApplied * pa)\n{', '''void CDirectorAI::requestRealized(PackageApplied * pa)
{
    if(pa->player == playerID && pa->packType == CTypeList::getInstance().getTypeID<GarrisonHeroSwap>(nullptr))
    {
        if(!garrisonSetupPending || static_cast<int>(pa->requestID) != garrisonSetupRequest)
            throw std::runtime_error("Garrison setup ACK tuple mismatch");
        const auto * town = cb->getTown(ObjectInstanceID(garrisonSetupTown));
        const auto * hero = cb->getHero(ObjectInstanceID(3));
        traceState("garrison_setup_ack_state");
        const bool verified = pa->result && town && hero && hero->getOwner() == playerID &&
            town->getOwner() == playerID && town->getGarrisonHero() == hero &&
            town->getVisitingHero() == nullptr && hero->isGarrisoned() &&
            hero->getVisitedTown() == town && hero->movementPointsRemaining() > 0;
        probeEvent("garrison_setup_ack", static_cast<int>(pa->requestID), verified ? 1 : 0);
        if(!verified) throw std::runtime_error("Garrison setup lacks real positive-MP garrison state");
        garrisonSetupPending = false;
        garrisonSetupDone = true;
        advanceTurn();
        return;
    }''')
    setup='''
bool CDirectorAI::setupGarrisonControl()
{
    const auto * hero = cb->getHero(ObjectInstanceID(3));
    if(!hero || hero->getOwner() != playerID || hero->isGarrisoned())
        throw std::runtime_error("Garrison fixture requires an actual owned visitor hero3");
    for(const auto * town : cb->getTownsInfo())
    {
        if(town->getOwner() != playerID || town->getVisitingHero() != hero) continue;
        if(town->getGarrisonHero() || hero->getVisitedTown() != town)
            throw std::runtime_error("Garrison fixture town identity mismatch");
        garrisonSetupTown = town->id.getNum();
        garrisonSetupPending = true;
        probeHero = 3;
        traceState("garrison_setup_before");
        probeEvent("garrison_setup_requested");
        cb->swapGarrisonHero(town);
        return true;
    }
    throw std::runtime_error("Fixture hero3 is not a real town visitor");
}

'''
    source=once(source,'bool CDirectorAI::issueEconomy()',setup+'bool CDirectorAI::issueEconomy()')
    source=once(source,'<< ",\\"ore\\":" << cb->getResourceAmount(GameResID::ORE) << ",\\"heroes\\":[";', '''<< ",\\"ore\\":" << cb->getResourceAmount(GameResID::ORE) << ",\\"resources\\":[";
    bool firstResource = true;
    for(auto res : {GameResID::WOOD, GameResID::MERCURY, GameResID::ORE, GameResID::SULFUR, GameResID::CRYSTAL, GameResID::GEMS, GameResID::GOLD})
    {
        if(!firstResource) out << ',';
        firstResource = false;
        out << cb->getResourceAmount(res);
    }
    out << "],\\"heroes\\":[";''')
    source=once(source,'<< ",\\"movement\\":" << hero->movementPointsRemaining() << ",\\"army\\":[";', '''<< ",\\"owner\\":" << hero->getOwner().getNum()
            << ",\\"garrisoned\\":" << (hero->isGarrisoned() ? "true" : "false")
            << ",\\"town_id\\":" << (hero->getVisitedTown() ? hero->getVisitedTown()->id.getNum() : -1)
            << ",\\"movement\\":" << hero->movementPointsRemaining() << ",\\"army\\":[";''')
    source=once(source,'<< town->id.getNum() << ",\\"buildings\\":[";', '''<< town->id.getNum()
            << ",\\"owner\\":" << town->getOwner().getNum()
            << ",\\"visitor_id\\":" << (town->getVisitingHero() ? town->getVisitingHero()->id.getNum() : -1)
            << ",\\"garrison_id\\":" << (town->getGarrisonHero() ? town->getGarrisonHero()->id.getNum() : -1)
            << ",\\"upper_army_id\\":" << town->getUpperArmy()->id.getNum()
            << ",\\"buildings\\":[";''')
    source=source.replace('multihero-scheduler-probe-v1','multihero-scheduler-garrison-v2')
    source=once(source,'\\"variant\\":\\"scheduler\\"','\\"variant\\":\\"garrison-v2\\"')
    baseline=source
    filtered=once(baseline,'hero->getOwner() != playerID || blockedHeroes.count(hero->id.getNum())',
                  'hero->getOwner() != playerID || hero->isGarrisoned() || blockedHeroes.count(hero->id.getNum())')
    for arm,cpp in [('baseline',baseline),('filtered',filtered)]:
        p=HERE/'candidates'/arm;p.mkdir(parents=True,exist_ok=True)
        for name,data in [('CDirectorAI.cpp',cpp),('CDirectorAI.h',header)]:
            target=p/name
            if target.exists():assert target.read_text()==data,'Preserve differing candidate'
            else:target.write_text(data)
    shutil.copy2(OLD/'capsule_support.py',HERE/'capsule_support.py')
    build=(OLD/'build_scheduler.py').read_text().replace("VARIANTS=('scheduler',)","VARIANTS=('baseline','filtered')")
    assert build.count("str(build_tree),'-v'")==2
    build=build.replace("str(build_tree),'-v'","str(build_tree),'-j4','-v'")
    (HERE/'build_scheduler.py').write_text(build)
    shutil.copy2(OLD/'fixture-01.vmap',HERE/'fixture-02.vmap')
    assert sha(HERE/'fixture-02.vmap')==sha(OLD/'fixture-01.vmap')
    (HERE/'common-setup.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),baseline.splitlines(True),fromfile='preserved-v1',tofile='garrison-common-setup')))
    (HERE/'single-factor.diff').write_text(''.join(difflib.unified_diff(baseline.splitlines(True),filtered.splitlines(True),fromfile='baseline',tofile='filtered')))
    (HERE/'DERIVATION.json').write_text(json.dumps(dict(passed=True,parent_cpp_sha256=sha(OLD/'candidates/scheduler/CDirectorAI.cpp'),
        fixture_map_sha256=sha(HERE/'fixture-02.vmap'),fixture_semantics='Unchanged map bytes plus actual GarrisonHeroSwap before any scheduling, positive-MP postnative garrison required',
        candidate_sha256={a:{n:sha(HERE/'candidates'/a/n) for n in ['CDirectorAI.cpp','CDirectorAI.h']} for a in ['baseline','filtered']},
        factor='Only eligibility hero->isGarrisoned() rejection; setup/instrumentation/fixture identical',native_runs=0,optimizer_steps=0),indent=2)+'\n')
    print('Derived two isolated candidates, exactly one scheduler predicate differs')
if __name__=='__main__':main()
