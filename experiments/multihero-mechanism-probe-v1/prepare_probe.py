#!/usr/bin/env python3
"""Generate review-only Director variants; NEVER installs, builds or launches."""
import argparse,difflib,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
AUDIT=HERE.parent/'strategic-fullgame-capability-audit'

def replace_method(source,name,body):
    matches=list(re.finditer(r'^[^\n]*\bCDirectorAI::\w+\([^\n]*',source,re.M))
    match=next(m for m in matches if re.search(r'::'+name+r'\(',m.group()))
    stop=next((m.start() for m in matches if m.start()>match.start()),len(source))
    return source[:match.start()]+body.rstrip()+'\n\n'+source[stop:]

PICK='''const CGHeroInstance * CDirectorAI::pickHero(std::vector<const CGHeroInstance *> & heroes) const
{
    if(probeMeetingSeen || probeFailed || probeEndAck) return nullptr;
    const CGHeroInstance * selected = nullptr;
    for(const auto * hero : heroes)
        if(hero && hero->getOwner() == playerID && !hero->isGarrisoned() &&
           !blockedHeroes.count(hero->id.getNum()) && hero->movementPointsRemaining() > 0 &&
           (!selected || hero->id.getNum() < selected->id.getNum())) selected = hero;
    return selected;
}'''
TARGET='''bool CDirectorAI::findTarget(const CGHeroInstance * hero, int3 & destination, std::string & reason) const
{
    const auto heroes = cb->getHeroesInfo();
    if(heroes.size() != 2) { probeEvent("fixture_hero_count_invalid"); return false; }
    const CGHeroInstance * other = nullptr;
    for(const auto * candidate : heroes)
        if(candidate && candidate != hero && candidate->getOwner() == playerID && !candidate->isGarrisoned()) other = candidate;
    if(!other || other->visitablePos() == hero->visitablePos()) { probeEvent("fixture_target_invalid"); return false; }
    CGPath path;
    pathfinder->invalidatePaths();
    if(!pathfinder->getPathsInfo(hero)->getPath(path, other->visitablePos()) ||
       !path.hasNextNode() || path.nextNode().turns != 0 || path.nextNode().coord == hero->visitablePos())
       { probeEvent("fixture_no_real_path"); return false; }
    destination = other->visitablePos();
    reason = "PURE_ENGINEERING_actual_owned_hero_meeting";
    return true;
}'''

EXTRA=r'''
void CDirectorAI::probeEvent(const std::string & event, int request, int result) const
{
    const char * path = std::getenv("LAB_HERO_PROBE_LOG");
    if(!path) return;
    std::ofstream out(path, std::ios::app);
    out << "{\"schema\":\"multihero-native-mechanism-probe-v1\",\"variant\":\"PROBE_VARIANT\",\"event\":\"" << event
        << "\",\"request_id\":" << request << ",\"result\":" << result
        << ",\"query_id\":" << probeQuery.getNum() << ",\"pending_move\":" << pendingMove
        << ",\"pending_queries\":" << pendingQueries.size() << ",\"query_requests\":" << queryRequests.size()
        << ",\"courier\":" << probeCourier.getNum() << ",\"receiver\":" << probeReceiver.getNum()
        << ",\"failed\":" << probeFailed << ",\"own_turn\":" << ownTurns << "}\n";
}

void CDirectorAI::probeClose()
{
    probeEvent("close_requested");
    cb->selectionMade(0, probeQuery);
}

void CDirectorAI::heroExchangeStarted(ObjectInstanceID hero1, ObjectInstanceID hero2, QueryID queryID)
{
    probeMeetingSeen = true;
    probeCourier = hero1;
    probeReceiver = hero2;
    probeQuery = queryID;
    probeEvent("exchange_callback");
    traceState("probe_before_exchange");
    // ORIGINAL_UNHANDLED_RETURN
    pendingQueries.insert(queryID);
    if(PROBE_TRANSFER)
    {
        const CGHeroInstance * donor = nullptr;
        const CGHeroInstance * receiver = nullptr;
        for(const auto * hero : cb->getHeroesInfo())
        {
            if(hero->id == hero1) donor = hero;
            if(hero->id == hero2) receiver = hero;
        }
        if(!donor || !receiver || donor->getOwner() != playerID || receiver->getOwner() != playerID ||
           donor->stacksCount() < 2 || receiver->stacksCount() < 1)
        {
            probeFailed = true; probeEvent("transfer_fixture_invalid"); probeClose(); return;
        }
        for(const auto & stack : donor->Slots())
        {
            const auto slot = receiver->getSlotFor(stack.second->getCreatureID());
            if(!slot.validSlot()) continue;
            // Whole one-stack transfer leaves donor's other stack and receiver's original army.
            probeTransferPending = true;
            pendingEconomy = true;
            traceState("probe_before_transfer");
            probeEvent("transfer_requested");
            cb->mergeOrSwapStacks(donor, receiver, stack.first, slot);
            return; // Query remains open until this exact ArrangeStacks request ACK.
        }
        probeFailed = true; probeEvent("transfer_no_legal_slot");
    }
    probeClose();
}
'''

ACK=r'''
    if(pa->player == playerID && pa->packType == CTypeList::getInstance().getTypeID<MoveHero>(nullptr))
        probeEvent("move_ack", static_cast<int>(pa->requestID), pa->result);
    if(pa->player == playerID && probeTransferPending && static_cast<int>(pa->requestID) == probeTransferRequest)
    {
        probeTransferPending = false;
        pendingEconomy = false;
        if(!pa->result) probeFailed = true;
        traceState("probe_after_transfer");
        probeEvent("transfer_ack", static_cast<int>(pa->requestID), pa->result);
        probeClose(); // Always release real query after recording success or failure.
        return;
    }
    if(pa->player == playerID && static_cast<int>(pa->requestID) == probeCloseRequest && probeCloseRequest >= 0)
    {
        probeCloseAck = pa->result;
        if(!pa->result) probeFailed = true;
        queryRequests.erase(static_cast<int>(pa->requestID));
        if(pa->result) pendingQueries.erase(probeQuery);
        traceState("probe_after_close");
        probeEvent("close_ack", static_cast<int>(pa->requestID), pa->result);
        advanceTurn();
        return;
    }
    if(pa->player == playerID && pa->packType == CTypeList::getInstance().getTypeID<EndTurn>(nullptr))
    {
        probeEndAck = pa->result;
        probeEvent("endturn_ack", static_cast<int>(pa->requestID), pa->result);
        traceState("probe_endturn_ack");
        if(pa->result && probeCloseAck && probeResolved && !probeFailed &&
           !pendingMove && pendingQueries.empty() && queryRequests.empty() && !probeTransferPending)
            probeEvent("probe_completed_nonterminal", static_cast<int>(pa->requestID), 1);
    }
'''
SENT=r'''
    if(dynamic_cast<const MoveHero *>(pack)) probeEvent("move_sent", requestID, -1);
    if(dynamic_cast<const EndTurn *>(pack)) probeEvent("endturn_sent", requestID, -1);
    if(probeTransferPending && dynamic_cast<const ArrangeStacks *>(pack))
    { probeTransferRequest = requestID; probeEvent("transfer_sent", requestID, -1); }
    if(auto reply = dynamic_cast<const QueryReply *>(pack))
        if(probeMeetingSeen && reply->qid == probeQuery)
        { probeCloseRequest = requestID; probeEvent("close_sent", requestID, -1); }
'''

def generate(out):
    source=(AUDIT/'CDirectorAI.cpp').read_text();header=(AUDIT/'CDirectorAI.h').read_text()
    expected=json.loads((AUDIT/'source-sha256.json').read_text())
    for name in ('CDirectorAI.cpp','CDirectorAI.h'):
        assert hashlib.sha256((AUDIT/name).read_bytes()).hexdigest()==expected['AI/DirectorAI/'+name]
    out.mkdir(exist_ok=False)
    for variant in ('original-unhandled','close-only','transfer-close'):
        cpp=replace_method(source,'pickHero',PICK)
        cpp=cpp.replace('#include <fstream>','#include <fstream>\n#include <stdexcept>')
        cpp=replace_method(cpp,'findTarget',TARGET)
        cpp=replace_method(cpp,'issueEconomy','bool CDirectorAI::issueEconomy()\n{ return false; }')
        cpp=replace_method(cpp,'traceDecision','')
        cpp=replace_method(cpp,'chooseExternalCandidate','')
        cpp=cpp.replace('\ttraceDecision(hero, destination, step);','\tprobeEvent("move_issued");')
        cpp=cpp.replace('movesThisTurn >= MAX_MOVES_PER_TURN','movesThisTurn >= 8')
        cpp=cpp.replace('\tadvanceTurn();\n}\n\nvoid CDirectorAI::advanceTurn()', '\tprobeEvent("turn_open");\n\tadvanceTurn();\n}\n\nvoid CDirectorAI::advanceTurn()')
        # No turn-start save and no external strategy request are needed by this probe.
        cpp=cpp.replace('cb->save("Saves/director-v5-initial", false);','probeEvent("save_disabled");')
        cpp=cpp.replace('\tcb = CB;','\tcb = CB;\n\tif(std::getenv("LAB_ADV_AGENT_DIR") || !std::getenv("LAB_HERO_PROBE_LOG"))\n\t\tthrow std::runtime_error("Engineering probe requires own log and forbids policy broker");',1)
        cpp=cpp.replace('void CDirectorAI::requestRealized(PackageApplied * pa)\n{','void CDirectorAI::requestRealized(PackageApplied * pa)\n{'+ACK)
        cpp=cpp.replace('void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)\n{','void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)\n{'+SENT)
        cpp=cpp.replace('void CDirectorAI::queryResolved(QueryID queryID)\n{','void CDirectorAI::queryResolved(QueryID queryID)\n{\n    if(probeMeetingSeen && queryID == probeQuery) { probeResolved = true; probeEvent("exchange_query_resolved"); }')
        cpp=cpp.replace('void CDirectorAI::yourTurn(QueryID queryID)\n{','void CDirectorAI::yourTurn(QueryID queryID)\n{\n    if(probeEndAck) { probeEvent("unexpected_additional_turn"); return; }')
        extra=EXTRA.replace('PROBE_VARIANT',variant).replace('PROBE_TRANSFER','true' if variant=='transfer-close' else 'false')
        extra=extra.replace('// ORIGINAL_UNHANDLED_RETURN','return; // Inherited original callback behavior: no QueryReply or transfer.' if variant=='original-unhandled' else '')
        cpp+='\n'+extra
        h=header.replace('private:\n','public:\n\tvoid heroExchangeStarted(ObjectInstanceID hero1, ObjectInstanceID hero2, QueryID queryID) override;\nprivate:\n',1)
        h=h.replace('\tbool issueMove();','''    bool probeMeetingSeen = false, probeFailed = false, probeEndAck = false;
    bool probeTransferPending = false, probeCloseAck = false, probeResolved = false;
    int probeTransferRequest = -1, probeCloseRequest = -1;
    QueryID probeQuery = QueryID(-1);
    ObjectInstanceID probeCourier, probeReceiver;
    void probeEvent(const std::string & event, int request = -1, int result = -1) const;
    void probeClose();
\tbool issueMove();''')
        h=re.sub(r'^\s*void traceDecision[^\n]*\n','\n',h,flags=re.M)
        h=re.sub(r'^\s*int chooseExternalCandidate[^\n]*\n','\n',h,flags=re.M)
        target=out/variant;target.mkdir()
        (target/'CDirectorAI.cpp').write_text(cpp);(target/'CDirectorAI.h').write_text(h)
        diff=''.join(difflib.unified_diff(source.splitlines(True),cpp.splitlines(True),fromfile='original/AI/DirectorAI/CDirectorAI.cpp',tofile=variant+'/AI/DirectorAI/CDirectorAI.cpp'))
        diff+=''.join(difflib.unified_diff(header.splitlines(True),h.splitlines(True),fromfile='original/AI/DirectorAI/CDirectorAI.h',tofile=variant+'/AI/DirectorAI/CDirectorAI.h'))
        (target/'source.diff').write_text(diff)
        assert 'strategy-candidates-v3' not in cpp and 'chooseExternalCandidate' not in cpp
    manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
    (out/'PREPARATION.json').write_text(json.dumps({'compiled':False,'installed':False,'games_started':0,'optimizer_steps':0,'parent_source_sha256':expected,'artifacts':manifest},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);generate(p.parse_args().out)
