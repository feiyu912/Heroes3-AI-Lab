"""Generate review-only native schema4 files from verified V8 archives; never installs/builds."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent
def replace_once(text,old,new):
 assert text.count(old)==1,old[:100]
 return text.replace(old,new,1)
def method(text,name,new):
 start=text.index(name);end=text.find('\n}\n',start)+3
 assert end>start
 return text[:start]+new.rstrip()+'\n'+text[end:]

HELPERS=r'''
std::string CDirectorAI::typedCandidateJSON(const Candidate & c) const
{
 if(c.endTurn) return "{\"op\":\"end_turn\"}";
 std::ostringstream out;
 out << "{\"op\":\"move\",\"kind\":" << c.kind << ",\"position\":[" << c.destination.x << ',' << c.destination.y
  << ',' << c.destination.z << "],\"next\":[" << c.next.x << ',' << c.next.y << ',' << c.next.z
  << "],\"path_cost\":" << c.cost << ",\"heuristic_score\":" << c.score << '}';
 return out.str();
}

void CDirectorAI::emitTyped(const std::string & json) const
{
 logGlobal->info("DirectorTypedEvent %s", json);
 const auto * explicitPath = std::getenv("LAB_ADV_TYPED_EVENTS");
 const auto * legacyPath = std::getenv("LAB_ADV_TRACE");
 if(!explicitPath && !legacyPath) return;
 const auto path = explicitPath ? std::string(explicitPath) : std::string(legacyPath) + ".typed.jsonl";
 std::ofstream out(path, std::ios::app | std::ios::binary);
 if(out) out << json << '\n';
}

void CDirectorAI::typedFailure(const std::string & reason) const
{
 typedProtocolFailed = true;
 logGlobal->error("DirectorTypedProtocolError %s", reason);
 traceState("typed_protocol_error");
 // Static reason identifiers only, never arbitrary broker text in JSON.
 emitTyped("{\"event\":\"typed_protocol_error\",\"player\":" + std::to_string(playerID.getNum()) +
  ",\"own_turn\":" + std::to_string(ownTurns) + "}");
}

void CDirectorAI::emitTypedBusy() const
{
 if(ownTurns<1) return;
 std::set<QueryID> queries = pendingQueries;
 for(const auto & entry : queryRequests) queries.insert(entry.second);
 std::ostringstream out;
 out << "{\"event\":\"busy_state\",\"player\":" << playerID.getNum() << ",\"own_turn\":" << ownTurns
  << ",\"query_count\":" << queries.size() << ",\"movement_busy\":" << (movementBusy || pendingMove ? "true" : "false")
  << ",\"economy_busy\":" << (pendingEconomy ? "true" : "false")
  << ",\"battle_busy\":" << (battleBusy ? "true" : "false") << '}';
 emitTyped(out.str());
}

void CDirectorAI::emitTypedAction(const std::string & event, const TypedContext & ctx, const std::string & extra) const
{
 std::ostringstream out;
 out << "{\"event\":\"" << event << "\",\"decision_id\":";
 if(ctx.automatic) out << "null"; else out << ctx.decisionID;
 out << ",\"native_request_id\":" << ctx.nativeRequestID << ",\"player\":" << ctx.player
  << ",\"hero\":" << ctx.hero << ",\"own_turn\":" << ctx.ownTurn << ",\"op\":\"" << ctx.op
  << "\",\"pack_type\":\"" << (ctx.op == "move" ? "MoveHero" : "EndTurn") << "\",\"selected_index\":";
 if(ctx.automatic) out << "null"; else out << ctx.selectedIndex;
 out << ",\"request_sha256\":";
 if(ctx.automatic) out << "null"; else out << '"' << ctx.requestSHA << '"';
 out << ",\"candidate\":" << ctx.candidateJSON;
 if(ctx.automatic) out << ",\"automatic_reason\":\"" << ctx.automaticReason << '"';
 else out << ",\"classification\":\"" << ctx.classification << '"';
 out << extra << '}';emitTyped(out.str());
}
'''

CHOOSE=r'''
int CDirectorAI::chooseExternalCandidate(const CGHeroInstance * hero) const
{
 const auto * directory = std::getenv("LAB_ADV_AGENT_DIR");
 if(!directory || ownTurns < 1 || cb->getHeroesInfo().size() != 1 || preparedTyped || outstandingTyped)
 { typedFailure("invalid_policy_request_state");return -1; }
 if(externalDecisionSerial >= static_cast<unsigned>(std::numeric_limits<int>::max()))
 { typedFailure("decision_counter_overflow");return -1; }
 char suffix[32];std::snprintf(suffix,sizeof(suffix),"%08u.json",++externalDecisionSerial);
 const std::string request = std::string(directory) + "/request-" + suffix;
 const std::string response = std::string(directory) + "/action-" + suffix;
 std::ostringstream out;
 out << "{\"schema\":\"strategy-candidates-v4\",\"request_id\":" << externalDecisionSerial
  << ",\"player\":" << playerID.getNum() << ",\"own_turn\":" << ownTurns << ",\"own_hero_count\":1"
  << ",\"day\":" << cb->getCalendar().getCurrentDay() << ",\"hero\":" << hero->id.getNum()
  << ",\"from\":[" << hero->visitablePos().x << ',' << hero->visitablePos().y << ',' << hero->visitablePos().z
  << "],\"gold\":" << cb->getResourceAmount(GameResID::GOLD) << ",\"wood\":" << cb->getResourceAmount(GameResID::WOOD)
  << ",\"ore\":" << cb->getResourceAmount(GameResID::ORE) << ",\"own_army_value\":" << ArmyDescriptor(hero,true).getStrength()
  << ",\"movement\":" << hero->movementPointsRemaining() << ",\"visible_threats\":[";
 bool first = true;
 for(const auto & threat : visibleThreats)
 {
  if(!first) out << ',';first=false;
  out << "{\"position\":[" << threat.first.x << ',' << threat.first.y << ',' << threat.first.z
   << "],\"approx_army_value\":" << threat.second << '}';
 }
 out << "],\"own_towns\":[";first=true;
 for(const auto * town : cb->getTownsInfo())
 {
  if(!first) out << ',';first=false;const int3 pos=town->visitablePos();
  out << "{\"position\":[" << pos.x << ',' << pos.y << ',' << pos.z
   << "],\"army_value\":" << ArmyDescriptor(town->getUpperArmy(),true).getStrength() << '}';
 }
 out << "],\"candidates\":[";first=true;std::vector<std::string> operations;
 for(const auto & c : candidates)
 {
  if(!first) out << ',';first=false;out << typedCandidateJSON(c);
  operations.push_back(c.endTurn ? "end_turn" : "move");
 }
 out << "]}\n";const auto requestBytes=out.str();const auto requestSHA=LabTypedPolicy::sha256(requestBytes);
 {
  std::ofstream file(request+".tmp",std::ios::binary);
  if(!file) { typedFailure("request_open_failed");return -1; }
  file << requestBytes;file.close();
  if(!file) { typedFailure("request_write_failed");return -1; }
 }
 if(std::rename((request+".tmp").c_str(),request.c_str())!=0)
 { typedFailure("request_publish_failed");return -1; }
 const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(30);
 while(std::chrono::steady_clock::now()<deadline)
 {
  std::ifstream file(response,std::ios::binary);
  if(file)
  {
   const std::string raw((std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());
   try
   {
    const auto selected=LabTypedPolicy::parseResponse(raw,static_cast<int>(externalDecisionSerial),playerID.getNum(),
       hero->id.getNum(),ownTurns,requestSHA,operations);
    TypedContext ctx;ctx.automatic=false;ctx.decisionID=static_cast<int>(externalDecisionSerial);
    ctx.player=playerID.getNum();ctx.hero=hero->id.getNum();ctx.ownTurn=ownTurns;
    ctx.op=selected.op;ctx.selectedIndex=selected.index;ctx.requestSHA=requestSHA;
    ctx.classification=selected.classification;ctx.candidateJSON=typedCandidateJSON(candidates[selected.index]);
    preparedTyped=ctx;return selected.index;
   }
   catch(const std::exception & error)
   { logGlobal->error("DirectorTypedResponseRejected %s",error.what());typedFailure("response_rejected");return -1; }
  }
  std::this_thread::sleep_for(std::chrono::milliseconds(1));
 }
 typedFailure("response_timeout");return -1;
}
'''

TURN=r'''
void CDirectorAI::yourTurn(QueryID queryID)
{
 // The immutable typed tuple survives even if old EndTurn ACK is still in flight.
 if(!outstandingTyped)
 {
  pendingMove=false;pendingHero=ObjectInstanceID();battleBusy=false;movementBusy=false;
 }
 turnActive=true;endingTurn=false;blockedHeroes.clear();committedTargets.clear();recruitedThisTurn.clear();
 ++ownTurns;traceState("turn_start");
 emitTyped("{\"event\":\"your_turn\",\"player\":"+std::to_string(playerID.getNum())+",\"own_turn\":"+std::to_string(ownTurns)+"}");
 if(!savedInitial) { savedInitial=true;cb->save("Saves/director-v5-initial",false); }
 movesThisTurn=0;
 if(queryID!=QueryID(-1)) { pendingQueries.insert(queryID);cb->selectionMade(0,queryID); }
 advanceTurn();
}
'''
ADVANCE=r'''
void CDirectorAI::advanceTurn()
{
 emitTypedBusy();
 if(!turnActive || typedProtocolFailed || endingTurn || pendingMove || pendingEconomy || battleBusy || movementBusy ||
    !pendingQueries.empty() || !queryRequests.empty() || outstandingTyped || preparedTyped) return;
 if(issueEconomy()) return;
 if(!issueMove()) finishTurn();
}
'''
FINISH=r'''
void CDirectorAI::finishTurn()
{
 if(!turnActive || typedProtocolFailed || outstandingTyped || pendingMove || pendingEconomy || battleBusy || movementBusy ||
    !pendingQueries.empty() || !queryRequests.empty()) return;
 if(preparedTyped && preparedTyped->op!="end_turn") { typedFailure("unconsumed_move_before_end_turn");return; }
 if(!preparedTyped)
 {
  TypedContext ctx;ctx.automatic=true;ctx.player=playerID.getNum();ctx.ownTurn=ownTurns;ctx.op="end_turn";
  const auto heroes=cb->getHeroesInfo();ctx.hero=heroes.empty() ? 0 : heroes.front()->id.getNum();
  ctx.candidateJSON="{\"op\":\"end_turn\"}";
  ctx.automaticReason=heroes.empty() ? "no_owned_hero" : (movesThisTurn>=MAX_MOVES_PER_TURN ? "native_move_budget" : "no_movable_hero");
  preparedTyped=ctx;
 }
 if(preparedTyped->ownTurn!=ownTurns) { typedFailure("stale_prepared_end_turn");return; }
 emitTypedBusy();endingTurn=true;traceState(preparedTyped->automatic ? "turn_end" : "before_end_turn");
 cb->endTurn(); // A genuine native EndTurn; never a same-position MoveHero.
}
'''
SENT=r'''
void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)
{
 if(auto reply=dynamic_cast<const QueryReply *>(pack)) queryRequests[requestID]=reply->qid;
 if(pendingEconomy && (dynamic_cast<const BuildStructure *>(pack) || dynamic_cast<const RecruitCreatures *>(pack) ||
    dynamic_cast<const ArrangeStacks *>(pack) || dynamic_cast<const HireHero *>(pack))) economyRequest=requestID;
 const bool move=dynamic_cast<const MoveHero *>(pack)!=nullptr;
 const bool end=dynamic_cast<const EndTurn *>(pack)!=nullptr;
 if(!move && !end) return;
 if(requestID<1 || !preparedTyped || outstandingTyped || preparedTyped->ownTurn!=ownTurns ||
    preparedTyped->op!=(move ? "move" : "end_turn")) { typedFailure("unbound_native_request");return; }
 outstandingTyped=*preparedTyped;outstandingTyped->nativeRequestID=requestID;preparedTyped.reset();
 emitTypedAction("native_action_sent",*outstandingTyped);
}
'''
ACK=r'''
void CDirectorAI::requestRealized(PackageApplied * pa)
{
 if(pa->player!=playerID) return;
 if(pendingEconomy && static_cast<int>(pa->requestID)==economyRequest)
 {
  pendingEconomy=false;logGlobal->info("DirectorAI: economy request finished id=%d success=%d",economyRequest,pa->result);
  traceState(pa->result ? "economy_applied" : "economy_failed");advanceTurn();
 }
 auto query=queryRequests.find(pa->requestID);
 if(query!=queryRequests.end())
 {
  if(pa->result) pendingQueries.erase(query->second);queryRequests.erase(query);advanceTurn();
 }
 const bool move=pa->packType==CTypeList::getInstance().getTypeID<MoveHero>(nullptr);
 const bool end=pa->packType==CTypeList::getInstance().getTypeID<EndTurn>(nullptr);
 if(!move && !end) return;
 if(!outstandingTyped || outstandingTyped->nativeRequestID!=static_cast<int>(pa->requestID) ||
    outstandingTyped->op!=(move ? "move" : "end_turn")) { typedFailure("unmatched_typed_ack");return; }
 const auto ctx=*outstandingTyped; // Save the old turn, never substitute the live ownTurns.
 emitTypedAction("package_applied",ctx,std::string(",\"source\":\"client\",\"package\":\"PackageApplied\",\"success\":")+(pa->result ? "true" : "false"));
 outstandingTyped.reset(); // Only this exact native request/op ACK can clear the tuple.
 if(move)
 {
  pendingMove=false;traceState(pa->result ? "move_applied" : "move_failed");
  if(!pa->result) blockedHeroes.insert(ctx.hero);
 }
 else if(ctx.ownTurn==ownTurns)
 {
  endingTurn=false;if(pa->result) turnActive=false;
 }
 if(!pa->result) typedFailure("native_action_ack_failed");
 advanceTurn(); // A late old EndTurn ACK resumes the already-started new turn safely.
}
'''
MOVED=r'''
void CDirectorAI::heroMoved(const TryMoveHero & details, bool verbose)
{
 if(!outstandingTyped || outstandingTyped->op!="move" || details.id.getNum()!=outstandingTyped->hero) return;
 if(outstandingTyped->moveResultSeen) { typedFailure("duplicate_move_result");return; }
 outstandingTyped->moveResultSeen=true;
 logGlobal->info("DirectorAI: step finished result=%d points_left=%d from %s to %s",static_cast<int>(details.result),
  details.movePoints,details.start.toString(),details.end.toString());
 // Evidence is the real received server TryMoveHero pack, not a fabricated reply.
 emitTypedAction("move_result",*outstandingTyped,",\"source\":\"server\",\"evidence\":\"received_TryMoveHero\",\"result\":"+std::to_string(static_cast<int>(details.result)));
 if(details.result==TryMoveHero::FAILED || details.start==details.end) blockedHeroes.insert(details.id.getNum());
 if(details.result==TryMoveHero::FAILED) typedFailure("native_move_failed");
}
'''

def main():
 cpp=(HERE/'baseline/AI/DirectorAI/CDirectorAI.cpp').read_text()
 hdr=(HERE/'baseline/AI/DirectorAI/CDirectorAI.h').read_text()
 hdr=replace_once(hdr,'\t\tdouble score;','\t\tdouble score;\n\t\tbool endTurn = false;')
 hdr=replace_once(hdr,'\tbool issueMove();',r'''
 struct TypedContext
 {
  bool automatic = false;bool moveResultSeen = false;
  int decisionID = -1;int nativeRequestID = -1;int player = 0;int hero = 0;int ownTurn = 0;int selectedIndex = -1;
  std::string op, requestSHA, candidateJSON, classification, automaticReason;
 };
 mutable std::optional<TypedContext> preparedTyped;
 std::optional<TypedContext> outstandingTyped;
 mutable bool typedProtocolFailed = false;
 std::string typedCandidateJSON(const Candidate & candidate) const;
 void emitTyped(const std::string & json) const;
 void emitTypedBusy() const;
 void emitTypedAction(const std::string & event, const TypedContext & ctx, const std::string & extra = "") const;
 void typedFailure(const std::string & reason) const;
 bool issueMove();''')
 cpp=replace_once(cpp,'#include "CDirectorAI.h"','#include "CDirectorAI.h"\n#include "TypedPolicyProtocol.h"\n#include <iterator>')
 cpp=replace_once(cpp,'\tbool found = false;','\tif(!std::getenv("LAB_ADV_AGENT_DIR")) { typedFailure("missing_agent_directory");return false; }\n\tbool found = false;')
 cpp=replace_once(cpp,'\tif(found && !std::getenv("LAB_ADV_AGENT_DIR"))\n\t\treturn true;\n','')
 cpp=replace_once(cpp,'\tif(found && std::getenv("LAB_ADV_AGENT_DIR"))','\tif(std::getenv("LAB_ADV_AGENT_DIR"))')
 cpp=replace_once(cpp,'\t\tconst int selected = chooseExternalCandidate(hero);','\t\tCandidate stop{};stop.endTurn=true;candidates.push_back(stop);\n\t\tconst int selected = chooseExternalCandidate(hero);')
 cpp=replace_once(cpp,'\t\tselectedCandidate = selected;','\t\tselectedCandidate = selected;\n\t\tif(candidates[selected].endTurn) { reason="typed_end_turn";return true; }')
 cpp=replace_once(cpp,'\tstd::vector<const CGHeroInstance *> heroes = cb->getHeroesInfo();','\tstd::vector<const CGHeroInstance *> heroes = cb->getHeroesInfo();\n\tif(heroes.size()>1) { typedFailure("single_hero_pilot_required");return false; }')
 old='''\t\tlogGlobal->info("DirectorAI: no target for hero %d", hero->id.getNum());
\t\tblockedHeroes.insert(hero->id.getNum());
\t\treturn issueMove();'''
 cpp=replace_once(cpp,old,'\t\ttypedFailure("typed_target_selection_failed");return false;')
 cpp=replace_once(cpp,'\tconst int3 here = hero->visitablePos();','\tif(!preparedTyped || preparedTyped->ownTurn!=ownTurns) { typedFailure("stale_prepared_action");return false; }\n\tif(candidates[selectedCandidate].endTurn) { finishTurn();return true; }\n\temitTypedBusy();\n\tconst int3 here = hero->visitablePos();')
 # A consumed policy proposal may never silently turn into automatic EndTurn.
 cpp=replace_once(cpp,'\t\t\treturn false;\n\t\t}\n\t\tconst CGPathNode next = path.nextNode();','\t\t\ttypedFailure("selected_move_path_changed");return false;\n\t\t}\n\t\tconst CGPathNode next = path.nextNode();')
 cpp=replace_once(cpp,'\t\t\treturn false;\n\t\t}\n\t\tstep = next.coord;','\t\t\ttypedFailure("selected_move_not_current_turn");return false;\n\t\t}\n\t\tstep = next.coord;')
 for signature,new in [('int CDirectorAI::chooseExternalCandidate(',CHOOSE),('void CDirectorAI::yourTurn(',TURN),
  ('void CDirectorAI::advanceTurn(',ADVANCE),('void CDirectorAI::finishTurn(',FINISH),('void CDirectorAI::requestSent(',SENT),
  ('void CDirectorAI::requestRealized(',ACK),('void CDirectorAI::heroMoved(',MOVED)]:cpp=method(cpp,signature,new)
 cpp=replace_once(cpp,'\t\tturnActive = false;','\t\tturnActive = false;\n\t\temitTyped("{\\\"event\\\":\\\"game_over\\\",\\\"completed\\\":true,\\\"player\\\":"+std::to_string(playerID.getNum())+",\\\"own_turn\\\":"+std::to_string(ownTurns)+"}");')
 # The legacy move-only decision log stays move-only but now serializes typed candidate payloads.
 old='''\t\tout << "{\\\"kind\\\":" << c.kind << ",\\\"position\\\":[" << c.destination.x << ',' << c.destination.y
\t\t\t<< ',' << c.destination.z << "],\\\"next\\\":[" << c.next.x << ',' << c.next.y << ',' << c.next.z
\t\t\t<< "],\\\"path_cost\\\":" << c.cost << ",\\\"heuristic_score\\\":" << c.score << '}';'''
 cpp=replace_once(cpp,old,'\t\tout << typedCandidateJSON(c);')
 cpp += '\n'+HELPERS
 cpp=cpp.replace('<< playerID.getNum()', '<< static_cast<int>(playerID.getNum())')
 for rel,text in [('AI/DirectorAI/CDirectorAI.cpp',cpp),('AI/DirectorAI/CDirectorAI.h',hdr)]:
  (HERE/'candidate'/rel).write_text(text,newline='\n')
 server=(HERE/'baseline/server/CGameHandler.cpp').read_text()
 server=replace_once(server,'#include "CGameHandler.h"','#include "CGameHandler.h"\n#include "../lib/networkPacks/PacksForServer.h"')
 marker=r'''
 auto traceTypedActionResult = [&](bool success)
 {
  const bool move = dynamic_cast<const MoveHero *>(&pack) != nullptr;
  if(!move && !dynamic_cast<const EndTurn *>(&pack)) return;
  logGlobal->info("TypedActionApplied player=%d native_request_id=%d op=%s success=%d",
   static_cast<int>(pack.player.getNum()),static_cast<int>(pack.requestID),move ? "move" : "end_turn",success ? 1 : 0);
 };
'''
 server=replace_once(server,'\tPackageReceived received(',marker+'\n\tPackageReceived received(')
 server=replace_once(server,'\t\tsendPackageResponse(false);','\t\ttraceTypedActionResult(false);\n\t\tsendPackageResponse(false);')
 server=replace_once(server,'\t\tsendPackageResponse(true);','\t\ttraceTypedActionResult(result); // Actual visitor result, before original ACK.\n\t\tsendPackageResponse(true);')
 (HERE/'candidate/server/CGameHandler.cpp').write_text(server,newline='\n')
 diffs=[];manifest={}
 for path in sorted((HERE/'candidate').rglob('*')):
  if not path.is_file():continue
  rel=path.relative_to(HERE/'candidate');base=HERE/'baseline'/rel
  manifest[str(rel).replace('\\','/')]=dict(baseline_sha256=hashlib.sha256(base.read_bytes()).hexdigest()if base.exists()else None,candidate_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
  if not base.exists()or base.read_bytes()!=path.read_bytes():
   diffs.extend(difflib.unified_diff(base.read_text().splitlines(True)if base.exists()else [],path.read_text().splitlines(True),fromfile='baseline/'+str(rel),tofile='candidate/'+str(rel)))
 (HERE/'candidate.diff').write_text(''.join(diffs))
 (HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(dict(schema='typed-native-source-candidate-v1',installed=False,compiled=False,native_runs=0,
   baseline_epoch='server-ready-v8/e198; no pressure-release A',candidate_epoch='schema4-client-plus-server-result-log',files=manifest),indent=2))
 print('Review candidate generated; active native tree untouched')

if __name__=='__main__':main()
