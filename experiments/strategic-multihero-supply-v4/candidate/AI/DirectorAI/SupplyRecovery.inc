#include "../../lib/CPlayerState.h"
#include "../../lib/json/JsonNode.h"
#include "../../lib/filesystem/Filesystem.h"
#include "../../lib/networkPacks/SaveLocalState.h"

namespace
{
 const std::string recoveryKey="heroes3_supply_v4";
 std::string recoveryEnv(const char*name)
 {const char*value=std::getenv(name);return value?std::string(value):std::string();}
 JsonNode recoveryJSON(const std::string&text,const std::string&name)
 {JsonParsingSettings options;options.strict=true;return JsonNode(text.data(),text.size(),options,name);}
 bool recoveryNonceValid(const std::string&value)
 {return !value.empty()&&value.size()<=96&&std::all_of(value.begin(),value.end(),[](unsigned char c){return (c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_';});}
}
std::string CDirectorAI::recoveryEconomy() const
{
 std::ostringstream out;
 for(int resource=0;resource<7;++resource)out<<cb->getResourceAmount(GameResID(resource))<<' ';
 for(const auto*t:cb->getTownsInfo())
 {
  out<<"town "<<t->id.getNum()<<' ';
  for(int building=0;building<44;++building)out<<t->hasBuilt(BuildingID(building));
  out<<' '<<t->creatures.size()<<' ';
  for(const auto&offer:t->creatures){out<<offer.first<<' '<<offer.second.size()<<' ';for(const auto&id:offer.second)out<<id.getNum()<<' ';}
 }
 return out.str();
}
supply_recovery_v4::Snapshot CDirectorAI::recoveryCurrent() const
{
 supply_recovery_v4::Snapshot s;s.control=supply;s.visited=supplyVisited;s.world=supplyWorld();s.economy=recoveryEconomy();
 s.source=supply_recovery_v4::sourceToken;s.nonce=recoveryNonce;s.player=playerID.getNum();s.day=cb->getCalendar().getCurrentDay();return s;
}
void CDirectorAI::recoveryEvent(const std::string&event,int request) const
{
 JsonNode row;row["schema"].String()="supply-native-checkpoint-events-v4";row["event"].String()=event;
 row["player"].Integer()=playerID.getNum();row["day"].Integer()=cb->getCalendar().getCurrentDay();row["own_turn"].Integer()=supply.turn;
 row["request_id"].Integer()=request;row["local_state_request_id"].Integer()=recoveryLocalRequest;row["save_request_id"].Integer()=recoverySaveRequest;
 row["owned_callback_pending"].Integer()=recoveryOwned.size();row["save_name"].String()=recoverySaveName;
 row["payload"]=recoveryPayload;row["source_token"].String()=supply_recovery_v4::sourceToken;
 row["current_control_text"].String()=supply_recovery_v4::encode(recoveryCurrent());
 const auto json=row.toCompactString();logGlobal->info("DirectorSupplyCheckpoint %s",json);
 const auto path=recoveryEnv("LAB_ADV_RECOVERY_EVENTS");
 if(!path.empty()){std::ofstream file(path,std::ios::app);file<<json<<'\n';file.flush();supply_recovery_v4::ensure(bool(file),"recovery_event_write_failed");}
}
void CDirectorAI::recoveryInit()
{
 using namespace supply_recovery_v4;
 const auto*player=cb->getPlayerState(playerID);
 ensure(player&&player->playerLocalSettings,"recovery_own_settings_missing");
 const JsonNode&embedded=(*player->playerLocalSettings)[recoveryKey];
 const auto bundlePath=recoveryEnv("LAB_ADV_RECOVERY_BUNDLE");
 if(!embedded.isNull() || !bundlePath.empty())
 {
  ensure(supplyMode()&&!embedded.isNull()&&!bundlePath.empty(),"recovery_load_requires_mode_bundle_and_native_payload");
  const auto bundle=recoveryJSON(readFile(bundlePath,16*1024*1024),bundlePath);
  ensure(bundle["epoch"].String()==epoch&&bundle["source_token"].String()==sourceToken,"recovery_bundle_epoch_or_source");
  ensure(bundle["payload"].toCompactString()==embedded.toCompactString(),"recovery_bundle_native_payload_mismatch");
  ensure(sha256(readFile(bundle["save_file"].String()))==bundle["save_sha256"].String(),"recovery_bundle_save_hash_mismatch");
  ensure(embedded["epoch"].String()==epoch&&embedded["source_token"].String()==sourceToken,"recovery_native_epoch_or_source");
  const auto text=embedded["control_text"].String();ensure(sha256(text)==embedded["control_sha256"].String(),"recovery_control_hash_mismatch");
  auto snapshot=decode(text);ensure(snapshot.source==sourceToken&&nontrivial(snapshot,2),"recovery_not_target_boundary");
  ensure(snapshot.player==playerID.getNum()&&snapshot.day==cb->getCalendar().getCurrentDay(),"recovery_player_or_day_mismatch");
  ensure(worldText(snapshot.world,snapshot.economy)==worldText(supplyWorld(),recoveryEconomy()),"recovery_native_world_mismatch");
  recoveryNonce=snapshot.nonce;recoveryPayload=embedded;recoverySaveName=embedded["save_name"].String();
  supply=snapshot.control;supplyVisited=snapshot.visited;pathfinder->invalidatePaths();
  recoveryResumePending=true;recoveryCheckpointDone=true;recoveryEvent("hydrated_native_payload",-1);return;
 }
 if(!supplyMode())return;
 const auto target=recoveryEnv("LAB_ADV_RECOVERY_CHECKPOINT_TURN");
 if(!target.empty())
 {
  ensure(target=="2","recovery_only_turn_two_supported");recoveryTargetTurn=2;recoveryNonce=recoveryEnv("LAB_ADV_RECOVERY_NONCE");
  ensure(recoveryNonceValid(recoveryNonce)&&!recoveryEnv("LAB_ADV_RECOVERY_EVENTS").empty(),"recovery_checkpoint_configuration_missing");
  recoverySaveName="Saves/supply-boundary-v4-"+recoveryNonce;
  ensure(!CResourceHandler::get()->existsResource(ResourcePath(recoverySaveName,EResType::SAVEGAME)),"recovery_refuses_existing_save");
 }
}
bool CDirectorAI::recoveryResumeTurn(QueryID q)
{
 if(!recoveryResumePending)return false;
 using namespace supply_recovery_v4;
 ensure(!turnActive&&!supply.pending&&supply.query<0&&!supplyTurnGate.waiting()&&supplyReplies.empty(),"recovery_resume_not_clean");
 const auto saved=decode(recoveryPayload["control_text"].String());
 ensure(encode(recoveryCurrent())==encode(saved),"recovery_state_changed_before_resumed_turn");
 recoveryResumePending=false;turnActive=true;endingTurn=false;movementBusy=false;battleBusy=false;
 supplyMoveSeen=false;recoveryEvent("resumed_saved_turn",-1);supplyTrace("hydrated_turn_resume");
 // This is the engine's actual resume notification, not a newly earned turn.
 // Do not call beginTurn, clear budgets/visited, choose roles or increment turn.
 if(q!=QueryID(-1))supplyQueueReply(q,0);else supplyAdvance();return true;
}
bool CDirectorAI::recoveryBeforeAdvance()
{
 using namespace supply_recovery_v4;
 if(recoveryLocalRequest==0||recoverySaveRequest==0||recoveryPersistenceBusy)return true;
 if(!turnActive||endingTurn||supply.pending||movementBusy||battleBusy||!supplyReplies.empty()||supplyReplyRequest>=0||supplyTurnGate.waiting()||!recoveryOwned.empty())return false;
 if((recoveryCheckpointDone||recoveryTargetTurn>0)&&recoveryBoundaryTurn!=supply.turn)
 {recoveryBoundaryTurn=supply.turn;recoveryEvent("own_turn_boundary",-1);}
 if(recoveryCheckpointDone||recoveryTargetTurn==0)return false;
 auto snapshot=recoveryCurrent();if(!nontrivial(snapshot,recoveryTargetTurn))return false;
 const auto text=encode(snapshot);(void)decode(text);
 recoveryPayload["epoch"].String()=epoch;recoveryPayload["source_token"].String()=sourceToken;
 recoveryPayload["nonce"].String()=recoveryNonce;recoveryPayload["save_name"].String()=recoverySaveName;
 recoveryPayload["control_text"].String()=text;recoveryPayload["control_sha256"].String()=sha256(text);
 // The server updates these settings. The current client's cached settings need
 // not be updated until a later native load; never use that cache as write proof.
 JsonNode local=*cb->getPlayerState(playerID)->playerLocalSettings;local[recoveryKey]=recoveryPayload;
 recoveryPersistenceBusy=true;recoveryLocalRequest=0;recoveryCheckpointDone=true;
 recoveryEvent("checkpoint_prepared",-1);cb->saveLocalState(local);return true;
}
bool CDirectorAI::recoverySent(const CPackForServer*pack,int request)
{
 using namespace supply_recovery_v4;
 ensure(request>0&&int(pack->requestID)==request&&pack->player==playerID,"recovery_request_identity_mismatch");
 int type=-1;
 // CTypeList supports polymorphic getTypeID via the concrete dynamic branches.
 if(dynamic_cast<const SaveLocalState*>(pack))type=CTypeList::getInstance().getTypeID<SaveLocalState>(nullptr);
 else if(dynamic_cast<const SaveGame*>(pack))type=CTypeList::getInstance().getTypeID<SaveGame>(nullptr);
 else type=CTypeList::getInstance().getTypeID(pack);
 ensure(recoveryOwned.emplace(request,std::make_pair(pack->player.getNum(),type)).second,"recovery_duplicate_owned_request");
 if(recoveryLocalRequest==0)
 {
  auto*actual=dynamic_cast<const SaveLocalState*>(pack);ensure(actual&&actual->data[recoveryKey].toCompactString()==recoveryPayload.toCompactString(),"recovery_actual_local_state_mismatch");
  recoveryLocalRequest=request;recoveryEvent("local_state_native_sent",request);return true;
 }
 if(recoverySaveRequest==0)
 {
  auto*actual=dynamic_cast<const SaveGame*>(pack);ensure(actual&&actual->fname==recoverySaveName&&!actual->notifySuccess&&actual->autosaveCountLimit==0,"recovery_actual_save_request_mismatch");
  recoverySaveRequest=request;recoveryEvent("save_native_sent",request);return true;
 }
 return false;
}
bool CDirectorAI::recoveryAck(PackageApplied*pa)
{
 using namespace supply_recovery_v4;
 if(pa->player!=playerID)return false;
 auto owned=recoveryOwned.find(pa->requestID);
 ensure(owned!=recoveryOwned.end()&&owned->second.first==pa->player.getNum()&&owned->second.second==pa->packType,"recovery_unbound_owned_ack");
 recoveryOwned.erase(owned); // real PackageApplied already received in this callback.
 if(int(pa->requestID)==recoveryLocalRequest&&recoveryPersistenceBusy&&recoverySaveRequest<0)
 {
  ensure(pa->packType==CTypeList::getInstance().getTypeID<SaveLocalState>(nullptr)&&pa->result&&recoveryOwned.empty(),"recovery_local_state_ack_failed");
  ensure(encode(recoveryCurrent())==recoveryPayload["control_text"].String(),"recovery_world_changed_during_local_write");
  recoveryEvent("local_state_real_ack",pa->requestID);recoverySaveRequest=0;cb->save(recoverySaveName,false);return true;
 }
 if(int(pa->requestID)==recoverySaveRequest&&recoveryPersistenceBusy)
 {
  ensure(pa->packType==CTypeList::getInstance().getTypeID<SaveGame>(nullptr)&&pa->result&&recoveryOwned.empty(),"recovery_save_ack_failed");
  ensure(encode(recoveryCurrent())==recoveryPayload["control_text"].String(),"recovery_world_changed_during_save");
  recoveryPersistenceBusy=false;recoveryEvent("checkpoint_snapshot",pa->requestID);
  // ACK is real, but gh.save can swallow file-write failure. External bundle
  // certification must additionally require successful-save marker and file SHA.
  supplyAdvance();return true;
 }
 return false;
}
