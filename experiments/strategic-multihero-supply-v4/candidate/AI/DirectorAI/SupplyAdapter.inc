// Included at end of CDirectorAI.cpp by prepare.py. No engine source is written by preparation.
namespace
{
 supply_v1::Pos supplyPos(const int3&p) {return {p.x,p.y,p.z};}
 int3 enginePos(const supply_v1::Pos&p) {return int3(p.x,p.y,p.z);}
 supply_v1::Army supplyArmy(const CArmedInstance*a)
 {
  supply_v1::Army result{};
  for(const auto&s:a->Slots()) result.at(s.first.getNum())={s.second->getCreatureID().getNum(),s.second->getCount()};
  return result;
 }
}
bool CDirectorAI::supplyMode() const
{ const char*mode=std::getenv("LAB_ADV_MODE");return mode && std::string(mode)=="scripted_supply_v1"; }
supply_v1::World CDirectorAI::supplyWorld() const
{
 supply_v1::World w;
 for(const auto*h:cb->getHeroesInfo())
 {
  supply_v1::Hero s;s.id=h->id.getNum();s.movement=h->movementPointsRemaining();
  s.garrison=false;
  for(const auto*t:cb->getTownsInfo()) if(t->getGarrisonHero()==h) s.garrison=true;
  s.boat=h->getBoat()!=nullptr;s.pos=supplyPos(h->visitablePos());s.army=supplyArmy(h);w.heroes.push_back(s);
 }
 for(const auto*t:cb->getTownsInfo())
 {
  // This first candidate never treats a garrison hero's army as the town army.
  if(t->getUpperArmy()!=t) continue;
  supply_v1::Town s;s.id=t->id.getNum();s.pos=supplyPos(t->visitablePos());s.army=supplyArmy(t->getUpperArmy());
  if(t->getVisitingHero()) s.visitor=t->getVisitingHero()->id.getNum();
  w.towns.push_back(s);
 }
 std::sort(w.heroes.begin(),w.heroes.end(),[](const auto&a,const auto&b){return a.id<b.id;});
 std::sort(w.towns.begin(),w.towns.end(),[](const auto&a,const auto&b){return a.id<b.id;});return w;
}
void CDirectorAI::supplyTrace(const std::string&event,int id,const std::string&actualRequest) const
{
 const char*path=std::getenv("LAB_ADV_SUPPLY_TRACE");
 const auto world=supplyWorld();
 std::ostringstream out;
 out<<"{\"schema\":\"scripted-supply-events-v3\",\"controller_epoch\":\"scripted-supply-cargo-v3\",\"event\":\""<<event<<"\",\"native_request_id\":"<<id
 <<",\"player\":"<<playerID.getNum()<<",\"day\":"<<cb->getCalendar().getCurrentDay()<<",\"own_turn\":"<<supply.turn
 <<",\"main\":"<<supply.main<<",\"courier\":"<<supply.courier<<",\"home\":"<<supply.home<<",\"phase\":"<<int(supply.phase)
 <<",\"query\":"<<supply.query<<",\"cursor\":"<<supply.cursor<<",\"cycles\":"<<supply.cycles
 <<",\"delivery_exchange\":"<<(supply.exchangeDelivery?"true":"false")<<",\"policy_transition\":false,\"roster\":[";
 bool first=true;for(const auto&h:world.heroes)
 {
  if(!first) out<<',';
  first=false;
  out<<"{\"id\":"<<h.id<<",\"position\":["<<h.pos.x<<','<<h.pos.y<<','<<h.pos.z<<"],\"movement\":"<<h.movement
  <<",\"garrison\":"<<(h.garrison?"true":"false")<<",\"boat\":"<<(h.boat?"true":"false")<<",\"budget_used\":";
  auto spent=supply.spent.find(h.id);out<<(spent==supply.spent.end()?0:spent->second)<<",\"army\":[";
  for(int i=0;i<7;++i) {if(i)out<<',';out<<'['<<h.army[i].creature<<','<<h.army[i].count<<']';}out<<"]}";
 }
 out<<"],\"towns\":[";
 first=true;for(const auto&t:world.towns)
 {
  if(!first) out<<',';
  first=false;
  out<<"{\"id\":"<<t.id<<",\"visitor\":"<<t.visitor<<",\"position\":["<<t.pos.x<<','<<t.pos.y<<','<<t.pos.z<<"],\"army\":[";
  for(int i=0;i<7;++i) {if(i)out<<',';out<<'['<<t.army[i].creature<<','<<t.army[i].count<<']';}
  out<<"]}";
 }
 out<<"],\"pending\":";
 if(!supply.pending) out<<"null";
 else
 {
  const auto&c=*supply.pending;
  out<<"{\"op\":"<<int(c.op)<<",\"actor\":"<<c.actor<<",\"target\":"<<c.target<<",\"source\":"<<c.source
  <<",\"from_slot\":"<<c.from<<",\"to_slot\":"<<c.to<<",\"destination\":["<<c.destination.x<<','<<c.destination.y<<','<<c.destination.z<<"]}";
 }
 out<<",\"actual_request\":"<<(actualRequest.empty()?"null":actualRequest)<<",\"job\":{\"id\":"<<supply.job
 <<",\"status\":"<<int(supply.jobStatus)<<",\"successful_jobs\":"<<supply.successfulJobs<<",\"incomplete_attempts\":"<<supply.incompleteAttempts
 <<",\"success\":"<<(supply.jobStatus==supply_v1::JobStatus::Delivered?"true":"false")<<",\"reason\":\""<<supply.deliveryReason<<"\",\"initial_reserve_slots\":[";
 for(int i=0;i<7;++i) {if(i)out<<',';out<<'['<<supply.initialReserve[i].creature<<','<<supply.initialReserve[i].count<<']';}
 out<<"],\"cargo_slots\":[";
 for(int i=0;i<7;++i) {if(i)out<<',';out<<'['<<supply.cargoSlots[i].creature<<','<<supply.cargoSlots[i].count<<']';}
 out<<']';
 auto ledger=[&](const char*name,const std::map<int,long long>&values)
 {out<<",\""<<name<<"\":[";bool first=true;for(const auto&p:values){if(!first)out<<',';first=false;out<<'['<<p.first<<','<<p.second<<']';}out<<']';};
 ledger("reserve",supply.reserve);ledger("picked",supply.picked);ledger("cargo_remaining",supply.cargo);ledger("delivered",supply.delivered);
 out<<"}}";
 const auto json=out.str();
 logGlobal->info("DirectorSupplyEvent %s",json);
 if(path) {std::ofstream file(path,std::ios::app);file<<json<<'\n';file.flush();}
}
void CDirectorAI::supplyQueueReply(QueryID q,int answer)
{
 if(supplyReplies.count(q.getNum())) {typedFailure("duplicate_supply_prompt");return;}
 supplyReplies[q.getNum()]=answer;supplyAdvance();
}
void CDirectorAI::supplyBegin(QueryID q)
{
 try
 {
  const bool oldEndPending=supply.pending && supply.pending->op==supply_v1::Op::End;
  if(supplyTurnGate.defer(oldEndPending,q.getNum())) {supplyTrace("new_turn_deferred_for_old_end_ack");return;}
  if(recoveryResumeTurn(q))return;
  // Native load integration is deliberately disabled until save/sidecar/load proof exists.
  if(std::getenv("LAB_ADV_SUPPLY_RESTORE")) throw std::runtime_error("supply_native_restore_not_qualified");
  if(supply.main<0) supply.start(supplyWorld());
  supply.beginTurn(supplyWorld());turnActive=true;endingTurn=false;
  supplyMoveSeen=false;supplyTrace("turn_start");
  if(q!=QueryID(-1)) supplyQueueReply(q,0);else supplyAdvance();
 }
 catch(const std::exception&e) {typedFailure(e.what());}
}
void CDirectorAI::supplyAdvance()
{
 try
 {
  if(!turnActive || typedProtocolFailed || supply.failed || endingTurn || supply.pending || supplyReplyRequest>=0) return;
  if(recoveryBeforeAdvance())return;
  // A queued genuine prompt is answered only after the previous scripted request ACK.
  if(!supplyReplies.empty())
  {
   auto it=supplyReplies.begin();supplyReplyQuery=it->first;
   supplyReplyRequest=0; // pre-dispatch reservation; requestSent binds the actual positive ID.
   cb->selectionMade(it->second,QueryID(it->first));return;
  }
  // Friendly exchange is inside the live movement query. It must be drained
  // while ONGOING_MOVEMENT stays blocked; only fresh movement waits for unblock.
  if(battleBusy || (movementBusy && supply.query<0)) return;
  auto w=supplyWorld();supply.validate(w);
  std::optional<supply_v1::Pos> mainGoal;
  // Fixed visible frontier patrol. Deterministic script, not the frozen model or expert data.
  const auto*mainHero=dynamic_cast<const CGHeroInstance*>(cb->getObj(ObjectInstanceID(supply.main)));
  if(!mainHero) throw std::runtime_error("main_hero_unavailable");
  pathfinder->invalidatePaths();auto paths=pathfinder->getPathsInfo(mainHero);
  const auto size=cb->getMapSize();double best=-1;
  for(int y=0;y<size.y;y+=3) for(int x=0;x<size.x;x+=3)
  {
   int3 p(x,y,mainHero->visitablePos().z);if(p==mainHero->visitablePos()) continue;
   CGPath path;if(!paths->getPath(path,p) || !path.hasNextNode() || path.nextNode().turns!=0) continue;
   double score=(cb->isVisible(p)?1.0:4.0)/(0.5+path.lastNode().cost);
   if(supplyVisited.count({x,y,p.z})) score*=0.05;
   if(score>best) {best=score;mainGoal=supplyPos(p);}
  }
  // Only internal yields may loop here. At most the two real actors are tried.
  for(int attempt=0;attempt<3;++attempt)
  {
   auto command=supply.next(w,mainGoal);if(!command) return;auto c=*command;
   if(c.op==supply_v1::Op::Move)
   {
    const auto*h=dynamic_cast<const CGHeroInstance*>(cb->getObj(ObjectInstanceID(c.actor)));
    if(!h) throw std::runtime_error("actor_unavailable");
    CGPath path;pathfinder->invalidatePaths();
    if(!pathfinder->getPathsInfo(h)->getPath(path,enginePos(c.destination)) || !path.hasNextNode() || path.nextNode().turns!=0)
    {supply.yield(c.actor,"no_current_turn_path");supplyTrace("actor_yield");continue;}
    supplyStep=h->convertFromVisitablePos(path.nextNode().coord);
    supplyMoveSeen=false;supply.prepare(c);supplyTrace("prepared");
    cb->moveHero(h,supplyStep,false,EPathfindingLayer::LAND);return;
   }
   supply.prepare(c);supplyTrace("prepared");
   if(c.op==supply_v1::Op::Transfer)
   {
    const auto*source=dynamic_cast<const CArmedInstance*>(cb->getObj(ObjectInstanceID(c.source)));
    const auto*target=dynamic_cast<const CArmedInstance*>(cb->getObj(ObjectInstanceID(c.target)));
    if(!source || !target) throw std::runtime_error("transfer_army_unavailable");
    cb->mergeOrSwapStacks(source,target,SlotID(c.from),SlotID(c.to));return;
   }
   if(c.op==supply_v1::Op::Close) {cb->selectionMade(0,QueryID(c.query));return;}
   endingTurn=true;cb->endTurn();return;
  }
  throw std::runtime_error("scheduler_internal_bound_exceeded");
 }
 catch(const std::exception&e) {typedFailure(e.what());}
}
void CDirectorAI::heroExchangeStarted(ObjectInstanceID a,ObjectInstanceID b,QueryID q)
{
 if(!supplyMode()) {typedFailure("exchange_requires_scripted_supply_mode");return;}
 try {supply.exchangeStarted(a.getNum(),b.getNum(),q.getNum());supplyTrace("exchange_open");supplyAdvance();}
 catch(const std::exception&e) {typedFailure(e.what());}
}
void CDirectorAI::supplySent(const CPackForServer*pack,int id)
{
 try
 {
  auto*move=dynamic_cast<const MoveHero*>(pack);auto*transfer=dynamic_cast<const ArrangeStacks*>(pack);
  auto*reply=dynamic_cast<const QueryReply*>(pack);auto*end=dynamic_cast<const EndTurn*>(pack);
  if(!move && !transfer && !reply && !end) return; // native battle requests stay in the owned ledger.
  if(pack->player!=playerID || int(pack->requestID)!=id) throw std::runtime_error("supply_native_identity_mismatch");
  // Observe the actual immutable pre-dispatch pack, independently of Command.
  const int packType=move?CTypeList::getInstance().getTypeID<MoveHero>(nullptr):
   transfer?CTypeList::getInstance().getTypeID<ArrangeStacks>(nullptr):
   reply?CTypeList::getInstance().getTypeID<QueryReply>(nullptr):CTypeList::getInstance().getTypeID<EndTurn>(nullptr);
  std::ostringstream actual;
  actual<<"{\"request_id\":"<<pack->requestID<<",\"player\":"<<pack->player.getNum()<<",\"pack_type\":"<<packType;
  if(move)
  {
   actual<<",\"op\":\"MoveHero\",\"hero\":"<<move->hid.getNum()<<",\"layer\":"<<int(move->layer)
    <<",\"transit\":"<<(move->transit?"true":"false")<<",\"path\":[";
   for(size_t i=0;i<move->path.size();++i) {if(i)actual<<',';const auto p=move->path[i];actual<<'['<<p.x<<','<<p.y<<','<<p.z<<']';}
   actual<<"]";
  }
  else if(transfer) actual<<",\"op\":\"ArrangeStacks\",\"source\":"<<transfer->id1.getNum()<<",\"target\":"<<transfer->id2.getNum()
   <<",\"from_slot\":"<<transfer->p1.getNum()<<",\"to_slot\":"<<transfer->p2.getNum()<<",\"what\":"<<int(transfer->what)<<",\"val\":"<<transfer->val;
  else if(reply) {actual<<",\"op\":\"QueryReply\",\"query\":"<<reply->qid.getNum()<<",\"reply\":";if(reply->reply)actual<<*reply->reply;else actual<<"null";}
  else actual<<",\"op\":\"EndTurn\",\"scope\":\"player\"";
  actual<<'}';
  if(supplyReplyRequest==0)
  {
   if(!reply || reply->qid.getNum()!=supplyReplyQuery || !reply->reply || *reply->reply!=supplyReplies.at(supplyReplyQuery))
    throw std::runtime_error("supply_prompt_payload_mismatch");
   supplyReplyRequest=id;supplyTrace("prompt_native_sent",id,actual.str());return;
  }
  if(!supply.pending) throw std::runtime_error("unprepared_supply_request");
  const auto&c=*supply.pending;
  supply_v1::Op op=move?supply_v1::Op::Move:transfer?supply_v1::Op::Transfer:reply?supply_v1::Op::Close:supply_v1::Op::End;
  if(move && (move->hid.getNum()!=c.actor || move->path.size()!=1 || move->path.front()!=supplyStep))
   throw std::runtime_error("supply_move_payload_mismatch");
  if(transfer && (transfer->id1.getNum()!=c.source || transfer->id2.getNum()!=c.target || transfer->p1.getNum()!=c.from || transfer->p2.getNum()!=c.to ||
    transfer->what!=(c.recipientBefore[c.to].count?2:1))) throw std::runtime_error("supply_transfer_payload_mismatch");
  if(reply && (reply->qid.getNum()!=c.query || !reply->reply || *reply->reply!=0)) throw std::runtime_error("supply_close_payload_mismatch");
  supply.bind(id,op);supplyTrace("native_sent",id,actual.str());
 }
 catch(const std::exception&e) {typedFailure(e.what());}
}
void CDirectorAI::supplyAck(PackageApplied*pa)
{
 if(pa->player!=playerID) return;
 try
 {
  if(int(pa->requestID)==supplyReplyRequest)
  {
   if(pa->packType!=CTypeList::getInstance().getTypeID<QueryReply>(nullptr) || !pa->result)
    throw std::runtime_error("supply_prompt_ack_failed");
   supplyTrace("prompt_real_ack",pa->requestID);supplyReplies.erase(supplyReplyQuery);supplyReplyQuery=-1;supplyReplyRequest=-1;supplyAdvance();return;
  }
  if(!supply.pending || int(pa->requestID)!=supply.request) return; // e.g. native BattleAI MakeAction ACK
  const auto c=*supply.pending;
  int expected=c.op==supply_v1::Op::Move?CTypeList::getInstance().getTypeID<MoveHero>(nullptr):
   c.op==supply_v1::Op::Transfer?CTypeList::getInstance().getTypeID<ArrangeStacks>(nullptr):
   c.op==supply_v1::Op::Close?CTypeList::getInstance().getTypeID<QueryReply>(nullptr):CTypeList::getInstance().getTypeID<EndTurn>(nullptr);
  if(pa->packType!=expected) throw std::runtime_error("supply_ack_type_mismatch");
  if(c.op==supply_v1::Op::Move && !supplyMoveSeen) throw std::runtime_error("supply_ack_without_move_result");
  supplyTrace(pa->result?"real_ack":"real_rejection",pa->requestID);supply.ack(pa->requestID,c.op,pa->result,supplyWorld());
  supplyTrace("control_ack_applied",pa->requestID);
  if(c.op==supply_v1::Op::End)
  {
   turnActive=false;endingTurn=false;
   auto queued=supplyTurnGate.afterEndAck();if(queued) supplyBegin(QueryID(*queued));return;
  }
  supplyAdvance();
 }
 catch(const std::exception&e) {typedFailure(e.what());}
}
void CDirectorAI::supplyMoved(const TryMoveHero&d)
{
 if(!supply.pending || supply.pending->op!=supply_v1::Op::Move || d.id.getNum()!=supply.pending->actor) return;
 if(supplyMoveSeen) {typedFailure("duplicate_supply_move_result");return;}
 supplyMoveSeen=true;
 if(d.result==TryMoveHero::FAILED) supply.yield(d.id.getNum(),"native_move_failed");
 else if(d.start==d.end && supply.query<0) supply.yield(d.id.getNum(),"no_displacement_without_exchange");
 const auto*h=dynamic_cast<const CGHeroInstance*>(cb->getObj(d.id));
 if(h) {const auto p=h->visitablePos();supplyVisited.insert({p.x,p.y,p.z});}
 supplyTrace("real_move_result");
}
