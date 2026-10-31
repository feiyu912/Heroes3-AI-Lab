"""Derive an isolated schema5 build candidate from the frozen nine-file capsule03 parent."""
import difflib,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'strategic-director-terminal-drain-v3'
BASE_MANIFEST=HERE.parent/'strategic-director-terminal-drain-v4/CANDIDATE_MANIFEST.json'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def change(text,a,b):
    assert text.count(a)==1,(a,text.count(a));return text.replace(a,b,1)
def main():
    baseline=json.loads(BASE_MANIFEST.read_text());texts={};original={}
    for relative,entry in baseline['files'].items():
        source=PARENT/'candidate'/relative
        assert sha(source)==entry['candidate_sha256']
        original[relative]=source.read_text();texts[relative]=original[relative]
    name='AI/DirectorAI/TypedPolicyProtocol.h';t=texts[name]
    t=change(t,'const std::string & requestSHA, const std::vector<std::string> & operations)','const std::string & requestSHA, const std::vector<std::string> & operations,\n const std::string & responseSchema = "strategy-typed-action-response-v1")')
    t=change(t,'str("schema")!="strategy-typed-action-response-v1"','str("schema")!=responseSchema')
    t+='\n'+(HERE/'BuildWire.inc').read_text();texts[name]=t
    name='AI/DirectorAI/CDirectorAI.h';t=texts[name]
    t=change(t,'void requestRealized(PackageApplied * pa) override;','void requestRealized(PackageApplied * pa) override;\n void buildChanged(const CGTownInstance * town, BuildingID buildingID, int what) override;')
    t=change(t,'bool endTurn = false;','bool endTurn = false;\n  bool build = false; int townID = -1; int buildingID = -1;\n  std::string category, costJSON;')
    t=change(t,'mutable std::optional<TypedContext> preparedTyped;','bool learnedBuildEnabled = false;\n LabLearnedBuild::Window buildWindow;\n void appendBuildCandidates() const;\n std::string buildTownState(int townID) const;\n bool issuePolicyBuild();\n mutable std::optional<TypedContext> preparedTyped;')
    # The pure protocol header is needed for the window type, not engine state.
    t=change(t,'#include "battle/AutocombatPreferences.h"','#include "battle/AutocombatPreferences.h"\n#include "TypedPolicyProtocol.h"')
    t=change(t,'bool automatic = false;bool moveResultSeen = false;','bool automatic = false;bool moveResultSeen = false;bool buildResultSeen = false;\n  int townID = -1;int buildingID = -1;std::string beforeBuildState;')
    texts[name]=t
    name='AI/DirectorAI/CDirectorAI.cpp';t=texts[name]
    t=change(t,'#include <iterator>','#include <iterator>\n#include "../../lib/entities/faction/CTown.h"\n#include "../../lib/entities/building/CBuilding.h"')
    t=change(t,'playerID = *cb->getPlayerID();','playerID = *cb->getPlayerID();\n try { learnedBuildEnabled=LabLearnedBuild::enabled(std::getenv("LAB_ADV_LEARNED_ECONOMY")); }\n catch(...) { typedFailure("invalid_learned_build_mode");return; }\n if(learnedBuildEnabled) logGlobal->info("DirectorLearnedEconomyEpoch player=%d epoch=learned-economy-build-v1 schema=strategy-candidates-v5",playerID.getNum());')
    # Parent already enters the external-selection block even with no moves.
    t=change(t,'Candidate stop{};stop.endTurn=true;candidates.push_back(stop);','if(learnedBuildEnabled && buildWindow.open) appendBuildCandidates();\n\t\tCandidate stop{};stop.endTurn=true;candidates.push_back(stop);')
    t=change(t,'if(candidates[selected].endTurn) { reason="typed_end_turn";return true; }','if(candidates[selected].endTurn) { reason="typed_end_turn";return true; }\n  if(candidates[selected].build) { reason="typed_build";return true; }')
    t=change(t,'const CGHeroInstance * hero = pickHero(heroes);','const CGHeroInstance * hero = pickHero(heroes);\n if(!hero && learnedBuildEnabled && buildWindow.open && heroes.size()==1) hero=heroes.front();')
    t=change(t,'if(candidates[selectedCandidate].endTurn) { finishTurn();return true; }','if(learnedBuildEnabled)\n {\n  if(!buildWindow.select(preparedTyped->op)) { typedFailure("build_window_violation");return false; }\n  if(candidates[selectedCandidate].build) return issuePolicyBuild();\n }\n if(candidates[selectedCandidate].endTurn) { finishTurn();return true; }')
    t=change(t,'++ownTurns;traceState("turn_start");','++ownTurns;if(learnedBuildEnabled) buildWindow.begin(ownTurns);traceState("turn_start");')
    t=change(t,'if(issueEconomy()) return;','if((!learnedBuildEnabled || !buildWindow.open || cb->getHeroesInfo().empty()) && issueEconomy()) return;')
    t=change(t,'for(const auto building : priorities)','if(!learnedBuildEnabled) for(const auto building : priorities)')
    t=change(t,'const bool end=pa->packType==CTypeList::getInstance().getTypeID<EndTurn>(nullptr);\n if(!move && !end) return;','const bool end=pa->packType==CTypeList::getInstance().getTypeID<EndTurn>(nullptr);\n const bool build=learnedBuildEnabled && pa->packType==CTypeList::getInstance().getTypeID<BuildStructure>(nullptr);\n if(!move && !end && !build) return;')
    t=change(t,'outstandingTyped->op!=(move ? "move" : "end_turn")','outstandingTyped->op!=(move ? "move" : (build ? "build" : "end_turn"))')
    t=change(t,'const auto ctx=*outstandingTyped; // Save the old turn, never substitute the live ownTurns.','const auto ctx=*outstandingTyped; // Save the old turn, never substitute the live ownTurns.\n if(build)\n {\n  emitTypedAction("build_ack_state",ctx,",\\"state\\":"+buildTownState(ctx.townID));\n  if(pa->result && !ctx.buildResultSeen) typedFailure("build_ack_without_received_structure");\n }')
    t=change(t,'else if(ctx.ownTurn==ownTurns)','else if(end && ctx.ownTurn==ownTurns)')
    t=change(t,'if(pendingEconomy && (dynamic_cast<const BuildStructure *>(pack) || dynamic_cast<const RecruitCreatures *>(pack) ||','if(pendingEconomy && ((!learnedBuildEnabled && dynamic_cast<const BuildStructure *>(pack)) || dynamic_cast<const RecruitCreatures *>(pack) ||')
    t=change(t,'const bool end=dynamic_cast<const EndTurn *>(pack)!=nullptr;\n if(!move && !end) return;','const bool end=dynamic_cast<const EndTurn *>(pack)!=nullptr;\n const auto * actualBuild=dynamic_cast<const BuildStructure *>(pack);\n const bool build=learnedBuildEnabled && actualBuild;\n if(!move && !end && !build) return;')
    t=change(t,'preparedTyped->op!=(move ? "move" : "end_turn")','preparedTyped->op!=(move ? "move" : (build ? "build" : "end_turn"))')
    t=change(t,'outstandingTyped=*preparedTyped;outstandingTyped->nativeRequestID=requestID;preparedTyped.reset();','if(build && (pendingEconomy || actualBuild->tid.getNum()!=preparedTyped->townID || actualBuild->bid.getNum()!=preparedTyped->buildingID))\n { typedFailure("actual_native_build_payload_mismatch");return; }\n outstandingTyped=*preparedTyped;outstandingTyped->nativeRequestID=requestID;preparedTyped.reset();')
    t=change(t,'emitTypedAction("native_action_sent",*outstandingTyped);','if(build)\n {\n  const auto & ctx=*outstandingTyped;\n  emitTypedAction("native_action_sent",ctx,",\\"actual_request\\":{\\"pack_type\\":\\"BuildStructure\\",\\"player\\":"+std::to_string(pack->player.getNum())+",\\"native_request_id\\":"+std::to_string(requestID)+",\\"town_id\\":"+std::to_string(actualBuild->tid.getNum())+",\\"building_id\\":"+std::to_string(actualBuild->bid.getNum())+"},\\"before_state\\":"+ctx.beforeBuildState);\n }\n else emitTypedAction("native_action_sent",*outstandingTyped);')
    t=change(t,'out << "{\\"schema\\":\\"strategy-candidates-v4\\",\\"request_id\\":" << externalDecisionSerial','out << "{\\"schema\\":\\"" << (learnedBuildEnabled ? "strategy-candidates-v5" : "strategy-candidates-v4") << "\\",\\"request_id\\":" << externalDecisionSerial')
    t=change(t,'out << "],\\"own_towns\\":[";first=true;','out << "]";\n if(learnedBuildEnabled) out << ",\\"economy_epoch\\":\\"learned-economy-build-v1\\",\\"economy_window_open\\":" << (buildWindow.open ? "true" : "false") << ",\\"resources\\":" << LabLearnedBuild::resources(cb->getResourceAmount());\n out << ",\\"own_towns\\":[";first=true;')
    t=change(t,'<< "],\\"army_value\\":" << ArmyDescriptor(town->getUpperArmy(),true).getStrength() << \'}\';','<< "],\\"army_value\\":" << ArmyDescriptor(town->getUpperArmy(),true).getStrength();\n  if(learnedBuildEnabled)\n  {\n   if(town->built<0 || town->getFactionID().getNum()<0) { typedFailure("invalid_own_town_state");return -1; }\n   out << ",\\"town_id\\":" << town->id.getNum() << ",\\"faction_id\\":" << town->getFactionID().getNum() << ",\\"built_today\\":" << town->built << ",\\"buildings\\":" << LabLearnedBuild::ids(town->getBuildings());\n  }\n  out << \'}\';')
    t=change(t,'operations.push_back(c.endTurn ? "end_turn" : "move");','operations.push_back(c.endTurn ? "end_turn" : (c.build ? "build" : "move"));')
    t=change(t,'hero->id.getNum(),ownTurns,requestSHA,operations);','hero->id.getNum(),ownTurns,requestSHA,operations,learnedBuildEnabled ? "strategy-typed-action-response-v2" : "strategy-typed-action-response-v1");')
    t=change(t,'preparedTyped=ctx;return selected.index;','if(candidates[selected.index].build) { ctx.townID=candidates[selected.index].townID;ctx.buildingID=candidates[selected.index].buildingID; }\n    preparedTyped=ctx;return selected.index;')
    t=change(t,'if(c.endTurn) return "{\\"op\\":\\"end_turn\\"}";','if(c.endTurn) return "{\\"op\\":\\"end_turn\\"}";\n if(c.build) return "{\\"op\\":\\"build\\",\\"actor\\":\\"player_town\\",\\"town_id\\":"+std::to_string(c.townID)+",\\"building_id\\":"+std::to_string(c.buildingID)+",\\"category\\":\\""+c.category+"\\",\\"cost\\":"+c.costJSON+"}";')
    t=change(t,'(ctx.op == "move" ? "MoveHero" : "EndTurn")','(ctx.op == "move" ? "MoveHero" : (ctx.op=="build" ? "BuildStructure" : "EndTurn"))')
    t=change(t,'out << extra << \'}\';emitTyped(out.str());','if(ctx.op=="build") out << ",\\"actor\\":\\"player_town\\",\\"town_id\\":" << ctx.townID << ",\\"building_id\\":" << ctx.buildingID;\n out << extra << \'}\';emitTyped(out.str());')
    t+='\n'+(HERE/'BuildAdapter.inc').read_text();texts[name]=t
    name='server/CGameHandler.cpp';t=texts[name]
    t=change(t,'if(!move && !dynamic_cast<const EndTurn *>(&pack)) return;','const auto * build=dynamic_cast<const BuildStructure *>(&pack);\n  const char * mode=std::getenv("LAB_ADV_LEARNED_ECONOMY");\n  if(!move && !dynamic_cast<const EndTurn *>(&pack) && !(build && mode && std::string(mode)=="build_v1")) return;')
    t=change(t,'move ? "move" : "end_turn",success ? 1 : 0);','move ? "move" : (build ? "build" : "end_turn"),success ? 1 : 0);\n  if(build) logGlobal->info("TypedBuildApplied player=%d native_request_id=%d town_id=%d building_id=%d success=%d",static_cast<int>(pack.player.getNum()),static_cast<int>(pack.requestID),build->tid.getNum(),build->bid.getNum(),success ? 1 : 0);')
    texts[name]=t
    name='client/NetPacksClient.cpp';t=texts[name]
    t=change(t,'#include <sstream>','#include <sstream>\n#include "../AI/DirectorAI/TypedPolicyProtocol.h"')
    t=change(t,'//todo: inform on actual resource set transferred','''if(const char * mode=std::getenv("LAB_ADV_LEARNED_ECONOMY")) if(std::string(mode)=="build_v1")
 {
  const std::string json="{\\"event\\":\\"set_resources_received\\",\\"player\\":"+std::to_string(pack.player.getNum())+",\\"mode\\":"+std::to_string(static_cast<int>(pack.mode))+",\\"resources\\":"+LabLearnedBuild::resources(pack.res)+"}";
  LabLearnedBuild::mirrorPack(json,[](const std::string & value){logGlobal->info("DirectorBuildPack %s",value);});
 }
 //todo: inform on actual resource set transferred''')
    t=change(t,'void ApplyClientNetPackVisitor::visitNewStructures(NewStructures & pack)\n{','''void ApplyClientNetPackVisitor::visitNewStructures(NewStructures & pack)
{
 if(const char * mode=std::getenv("LAB_ADV_LEARNED_ECONOMY")) if(std::string(mode)=="build_v1")
 {
  const std::string json="{\\"event\\":\\"new_structures_received\\",\\"town_id\\":"+std::to_string(pack.tid.getNum())+",\\"built_today\\":"+std::to_string(pack.built)+",\\"buildings\\":"+LabLearnedBuild::ids(pack.bid)+"}";
  LabLearnedBuild::mirrorPack(json,[](const std::string & value){logGlobal->info("DirectorBuildPack %s",value);});
 }''')
    texts[name]=t
    entries={};diff=[]
    for relative,text in texts.items():
        dest=HERE/'candidate'/relative;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
        entries[relative]=dict(baseline_sha256=baseline['files'][relative]['baseline_sha256'],parent_candidate_sha256=baseline['files'][relative]['candidate_sha256'],candidate_sha256=sha(dest))
        diff+=list(difflib.unified_diff(original[relative].splitlines(True),text.splitlines(True),fromfile='capsule03/'+relative,tofile='learned-build-v1/'+relative))
    (HERE/'candidate.diff').write_text(''.join(diff))
    write(HERE/'CANDIDATE_MANIFEST.json',dict(schema='director-learned-economy-build-v1',parent_manifest_sha256=sha(BASE_MANIFEST),contract_sha256=sha(HERE/'CONTRACT.md'),files=entries))
    write(HERE/'MANIFEST.json',dict(candidate_files={r:e['candidate_sha256'] for r,e in entries.items()},native_builds=0,native_games=0,optimizer_steps=0))
if __name__=='__main__':main()
