#include "SupplyController.h"
#include <iostream>
#include <functional>
#include <cstdlib>
using namespace supply_v1;
int checks=0;
void check(bool ok,const char*message) {++checks;if(!ok){std::cerr<<message<<'\n';std::exit(1);}}
void rejects(std::function<void()>f,const char*message)
{try{f();}catch(const std::runtime_error&){++checks;return;}check(false,message);}
World fixture()
{
 World w;Hero m;m.id=8;m.pos={8,4,0};m.movement=1000;m.army[0]={0,5};
 Hero c;c.id=19;c.pos={2,4,0};c.movement=1000;c.army[0]={0,10};c.army[1]={2,3};w.heroes={c,m};
 Town t;t.id=3;t.visitor=19;t.pos=c.pos;t.army[0]={4,12};w.towns={t};return w;
}
Controller ready(World&w) {Controller c;c.start(w);c.beginTurn(w);return c;}
void applyTransfer(World&w,const Command&c)
{
 Army*donor=c.delivery?&w.heroes[0].army:&w.towns[0].army;
 Army*recipient=c.delivery?&w.heroes[1].army:&w.heroes[0].army;
 auto stack=(*donor)[c.from];(*donor)[c.from]=Stack{};
 (*recipient)[c.to].creature=stack.creature;(*recipient)[c.to].count+=stack.count;
}
int main()
{
 {
  TurnBoundaryGate gate;check(!gate.defer(false,100),"ordinary new turn starts immediately");
  check(!gate.afterEndAck(),"ACK before next turn has no deferred event");
  check(gate.defer(true,101) && gate.waiting(),"new turn before EndTurn ACK deferred");
  rejects([&]{gate.defer(true,102);},"duplicate new turn event accepted");
  auto q=gate.afterEndAck();check(q && *q==101 && !gate.waiting(),"exact queued query survives old ACK");
  check(!gate.defer(false,*q),"queued new turn begins after old ACK");
  check(gate.defer(true,-1),"queryless new turn also deferred");
  q=gate.afterEndAck();check(q && *q==-1,"queryless sentinel preserved without fabricated reply");
 }
 World w=fixture();auto c=ready(w);
 check(c.main==8 && c.courier==19 && c.home==3,"stable actual role IDs");
 auto first=c.next(w,Pos{9,4,0});check(first && first->actor==8 && first->op==Op::Move,"main first");
 c.prepare(*first);c.bind(10,Op::Move);
 check(!c.next(w,Pos{9,4,0}),"no second request while pending");
 check(!c.boundary(false,false,false,false),"pending forbids save boundary");
 {auto copy=c;rejects([&]{copy.prepare(*first);},"double pending allowed");}
 {auto copy=c;rejects([&]{copy.bind(11,Op::Move);},"rebind allowed");}
 {auto copy=c;rejects([&]{copy.ack(11,Op::Move,true,w);},"wrong ACK ID");}
 {auto copy=c;rejects([&]{copy.ack(10,Op::Close,true,w);},"wrong ACK op");}
 {auto copy=c;rejects([&]{copy.ack(10,Op::Move,false,w);},"negative ACK accepted");}
 c.ack(10,Op::Move,true,w);
 auto pickup=c.next(w,Pos{9,4,0});check(pickup && pickup->op==Op::Transfer && !pickup->delivery,"actual visiting town pickup");
 check(pickup->actor==19 && pickup->source==3 && pickup->target==19,"pickup honest actor and town IDs");
 c.prepare(*pickup);c.bind(12,Op::Transfer);
 {auto copy=c;rejects([&]{copy.ack(12,Op::Transfer,true,w);},"ACK without donor delta");}
 applyTransfer(w,*pickup);c.ack(12,Op::Transfer,true,w);
 check(w.heroes[0].army[2].count==12 && w.towns[0].army[0].count==0,"whole stack pickup conserves army");
 c.next(w,Pos{9,4,0}); // main actor internal selection, intentionally not issued
 auto meeting=c.next(w,Pos{9,4,0});
 check(meeting && meeting->actor==19 && meeting->target==8 && meeting->destination==w.heroes[1].pos,"meeting binds main ID");
 c.prepare(*meeting);c.bind(13,Op::Move);
 c.yield(19,"no_displacement_without_exchange");const auto spentBefore=c.spent[19];
 c.exchangeStarted(19,8,77);check(c.phase==Phase::Exchange && c.query==77,"real exchange callback accepted before movement ACK");
 check(!c.blocked.count(19) && c.spent[19]==spentBefore,"real exchange clears only provisional zero-displacement block without resetting budget");
 check(!c.next(w,{}),"exchange cannot transfer before movement ACK");
 c.ack(13,Op::Move,true,w);
 int rq=14,transfers=0;
 while(true)
 {
  auto cmd=c.next(w,{});check(bool(cmd),"exchange produces transaction");
  if(cmd->op==Op::Close)
  {
   check(cmd->query==77,"close actual query ID");c.prepare(*cmd);c.bind(rq,Op::Close);
   check(c.query==77 && c.phase==Phase::Exchange,"sent close is not query closure");
   c.ack(rq,Op::Close,true,w);break;
  }
  check(cmd->delivery && cmd->source==19 && cmd->target==8,"delivery correct role IDs");
  c.prepare(*cmd);c.bind(rq,Op::Transfer);applyTransfer(w,*cmd);c.ack(rq,Op::Transfer,true,w);++rq;++transfers;
 }
 check(transfers==1 && occupied(w.heroes[0].army)==2,"donor retains entire initial reserve");
 check(w.heroes[1].army[0].count==5 && w.heroes[1].army[1].creature==4 && w.heroes[1].army[1].count==12,"only actual pickup cargo delivered");
 check(c.successfulJobs==1 && c.cargo.empty() && c.picked==c.delivered,"job completion requires all cargo exact ACKs and query close");
 check(c.query<0 && c.phase==Phase::Return && c.cycles==1,"close ACK alone drains exchange without QueryResolved");
 check(c.boundary(false,false,false,false),"clean boundary");
 check(!c.boundary(true,false,false,false),"movement forbids boundary");
 check(!c.boundary(false,true,false,false),"battle forbids boundary");
 check(!c.boundary(false,false,true,false),"query forbids boundary");
 check(!c.boundary(false,false,false,true),"owned requests forbid boundary");
 c.phase=Phase::Meeting;c.goals[19]={8,4,0};c.beginTurn(w);
 check(c.phase==Phase::Meeting && c.main==8 && c.goals[19]==Pos{8,4,0},"persistent state across own turns");
 w.heroes[1].pos={12,4,0};c.cursor=1;auto moved=c.next(w,Pos{9,4,0});
 check(moved && moved->target==8 && moved->destination==Pos{12,4,0},"moving receiver target refreshes by stable ID");
 {auto copy=c;copy.spent[19]=Controller::budget;copy.cursor=1;auto next=copy.next(w,Pos{9,4,0});check(next && next->actor==8,"courier cap cannot consume main budget");}
 {auto copy=c;copy.spent[8]=Controller::budget;copy.cursor=0;auto next=copy.next(w,{});check(next && next->actor==19,"main cap cannot consume courier budget");}
 {auto copy=c;auto world=w;world.heroes[0].garrison=true;copy.cursor=1;auto next=copy.next(world,Pos{9,4,0});check(next && next->actor==8,"garrison hero excluded");}
 {auto copy=c;auto world=w;world.heroes[0].boat=true;copy.cursor=1;auto next=copy.next(world,Pos{9,4,0});check(next && next->actor==8,"naval actor excluded");}
 {auto copy=c;copy.spent[8]=copy.spent[19]=Controller::budget;auto next=copy.next(w,{});check(next && next->op==Op::End && next->actor==-1,"only player-wide EndTurn");}
 {auto copy=c;auto world=w;world.heroes.pop_back();rejects([&]{copy.next(world,{});},"missing receiver accepted");}
 {auto copy=c;auto world=w;world.heroes.push_back(world.heroes[0]);rejects([&]{copy.next(world,{});},"third hero accepted");}
 {auto copy=c;auto world=w;world.heroes[0].id=world.heroes[1].id;rejects([&]{copy.next(world,{});},"duplicate roster ID accepted");}
 {auto copy=c;auto world=w;world.towns.clear();rejects([&]{copy.next(world,{});},"lost town accepted");}
 {auto copy=c;rejects([&]{copy.exchangeStarted(8,99,78);},"foreign hero exchange accepted");}
 {auto copy=c;copy.phase=Phase::Return;copy.exchangeStarted(8,19,78);
  auto close=copy.next(w,{});check(close && close->op==Op::Close,"accidental friendly meeting closes without transfer");
  copy.prepare(*close);copy.bind(90,Op::Close);copy.ack(90,Op::Close,true,w);
  check(copy.phase==Phase::Return && copy.cycles==c.cycles,"accidental meeting restores job without delivery cycle");}
 {auto world=fixture();auto ctrl=ready(world);ctrl.phase=Phase::Exchange;ctrl.query=4;
  ctrl.exchangeDelivery=true;
  for(int i=0;i<7;++i) world.heroes[1].army[i]={100+i,1};
  auto cmd=ctrl.next(world,{});check(cmd && cmd->op==Op::Close,"seven incompatible recipient slots close without swapping");}
 {auto world=fixture();world.heroes[0].army[1]=Stack{};auto ctrl=ready(world);ctrl.phase=Phase::Exchange;ctrl.query=4;
  ctrl.exchangeDelivery=true;
  auto cmd=ctrl.next(world,{});check(cmd && cmd->op==Op::Close,"one donor stack never transferred");}
 {auto world=fixture();auto ctrl=ready(world);ctrl.phase=Phase::Pickup;world.towns[0].visitor=-1;ctrl.cursor=1;
  rejects([&]{ctrl.next(world,{});},"remote pickup accepted");}
 {auto world=fixture();auto ctrl=ready(world);ctrl.cursor=1;world.towns[0].visitor=-1;
  auto cmd=ctrl.next(world,{});check(cmd && cmd->op==Op::End,"same position is not fake native interaction");}
 // Regression from actual v2 native probe: slot0=3 Archers reserve, pickup
 // slot1=10 Pikemen. Only the slot1 cargo can leave, regardless of slot order.
 auto nativeFixture=[] {auto world=fixture();world.heroes[0].army=Army{};world.heroes[0].army[0]={2,3};world.towns[0].army=Army{};world.towns[0].army[0]={0,10};return world;};
 auto pickupCargo=[](Controller&ctrl,World&world,int requestID)
 {
  ctrl.cursor=1;auto cmd=ctrl.next(world,Pos{9,4,0});check(cmd && cmd->op==Op::Transfer && !cmd->delivery,"pickup actual town command");
  ctrl.prepare(*cmd);ctrl.bind(requestID,Op::Transfer);applyTransfer(world,*cmd);ctrl.ack(requestID,Op::Transfer,true,world);
 };
 auto meet=[](Controller&ctrl,World&world,int q)
 {
  ctrl.cursor=1;auto move=ctrl.next(world,Pos{9,4,0});check(move && move->op==Op::Move && move->target==ctrl.main,"cargo meeting target");
  ctrl.prepare(*move);ctrl.bind(q-1,Op::Move);ctrl.exchangeStarted(ctrl.courier,ctrl.main,q);ctrl.ack(q-1,Op::Move,true,world);
 };
 {
  auto world=nativeFixture();auto ctrl=ready(world);
  check(ctrl.reserve==std::map<int,long long>{{2,3}} && ctrl.cargo.empty(),"initial reserve captured from actual army, not cargo");
  ctrl.cursor=1;auto p=ctrl.next(world,{});ctrl.prepare(*p);ctrl.bind(101,Op::Transfer);
  check(ctrl.cargo.empty() && ctrl.picked.empty() && ctrl.job==0,"send does not register unACKed cargo");
  applyTransfer(world,*p);ctrl.ack(101,Op::Transfer,true,world);
  check(ctrl.cargo==std::map<int,long long>{{0,10}} && ctrl.picked==ctrl.cargo && ctrl.reserve.at(2)==3,"positive exact pickup ACK adds provenance");
  ctrl.beginTurn(world);ctrl.beginTurn(world);check(ctrl.cargo.at(0)==10 && ctrl.job==1,"cargo job persists across own turns");
  meet(ctrl,world,110);auto d=ctrl.next(world,{});
  check(d && d->delivery && d->from==1 && d->to==0 && d->donorBefore[1].count==10,"deliver pike cargo instead of first-slot archer reserve");
  {auto copy=ctrl;auto bad=*d;bad.from=0;rejects([&]{copy.prepare(bad);},"initial reserve passed as cargo");}
  ctrl.prepare(*d);ctrl.bind(111,Op::Transfer);applyTransfer(world,*d);ctrl.ack(111,Op::Transfer,true,world);
  check(ctrl.cargo.empty() && ctrl.delivered.at(0)==10 && ctrl.successfulJobs==0 && ctrl.jobStatus==JobStatus::Carrying,"delivery ACK alone is not closed success");
  auto close=ctrl.next(world,{});ctrl.prepare(*close);ctrl.bind(112,Op::Close);
  check(ctrl.successfulJobs==0,"sent close is not success");ctrl.ack(112,Op::Close,true,world);
  check(ctrl.successfulJobs==1 && ctrl.jobStatus==JobStatus::Delivered && world.heroes[0].army[0].count==3 && world.heroes[1].army[0].count==15,"actual probe objective: main15pike, courier3archer, townempty");
 }
 {
  auto world=nativeFixture();world.heroes[0].army[0]={0,3};auto ctrl=ready(world);pickupCargo(ctrl,world,120);
  check(world.heroes[0].army[0].count==13 && ctrl.cargo.at(0)==10 && ctrl.reserve.at(0)==3,"same creature merge ledger separates reserve and cargo");
  meet(ctrl,world,130);auto close=ctrl.next(world,{});check(close && close->op==Op::Close,"merged cargo cannot whole-stack preserve reserve; no split");
  ctrl.prepare(*close);ctrl.bind(131,Op::Close);ctrl.ack(131,Op::Close,true,world);
  check(ctrl.successfulJobs==0 && ctrl.incompleteAttempts==1 && ctrl.jobStatus==JobStatus::Incomplete && ctrl.cargo.at(0)==10,"same-creature close explicitly incomplete retains cargo");
 }
 {
  auto world=nativeFixture();world.heroes[0].army[0]={0,3};world.heroes[0].army[1]={0,2};world.heroes[0].army[2]={2,1};
  auto ctrl=ready(world);pickupCargo(ctrl,world,132);meet(ctrl,world,135);auto close=ctrl.next(world,{});
  check(close && close->op==Op::Close && world.heroes[0].army[1].count==2,"same-creature initial small slot is not acknowledged cargo");
  ctrl.prepare(*close);ctrl.bind(136,Op::Close);ctrl.ack(136,Op::Close,true,world);
  check(ctrl.successfulJobs==0 && ctrl.jobStatus==JobStatus::Incomplete && ctrl.delivered.empty(),"multi-slot same-creature reserve conservatively incomplete without split");
 }
 {
  auto world=nativeFixture();auto ctrl=ready(world);pickupCargo(ctrl,world,140);
  for(int i=0;i<7;++i)world.heroes[1].army[i]={100+i,1};
  meet(ctrl,world,150);auto close=ctrl.next(world,{});check(close && close->op==Op::Close && ctrl.deliveryReason=="recipient_has_no_compatible_slot","full incompatible receiver cannot swap away cargo");
  ctrl.prepare(*close);ctrl.bind(151,Op::Close);ctrl.ack(151,Op::Close,true,world);
  check(ctrl.successfulJobs==0 && ctrl.cargo.at(0)==10 && ctrl.delivered.empty(),"blocked delivery is incomplete, never successful");
 }
 {
  auto world=nativeFixture();world.towns[0].army[1]={4,7};auto ctrl=ready(world);pickupCargo(ctrl,world,160);pickupCargo(ctrl,world,161);
  for(int i=1;i<7;++i)world.heroes[1].army[i]={100+i,1};
  meet(ctrl,world,170);auto d=ctrl.next(world,{});check(d && d->delivery && d->donorBefore[d->from].creature==0,"partially compatible cargo can deliver matching creature");
  ctrl.prepare(*d);ctrl.bind(171,Op::Transfer);applyTransfer(world,*d);ctrl.ack(171,Op::Transfer,true,world);
  auto close=ctrl.next(world,{});check(close && close->op==Op::Close,"remaining incompatible cargo closes");
  ctrl.prepare(*close);ctrl.bind(172,Op::Close);ctrl.ack(172,Op::Close,true,world);
  check(ctrl.jobStatus==JobStatus::Incomplete && ctrl.successfulJobs==0 && ctrl.delivered.at(0)==10 && ctrl.cargo.at(4)==7 && ctrl.picked.size()==2,"partial delivery explicit outstanding ledger");
  ctrl.beginTurn(world);check(ctrl.cargo.at(4)==7 && ctrl.picked.at(0)==10 && ctrl.incompleteAttempts==1,"partial cargo persists after close and next turn");
 }
 {
  auto world=nativeFixture();auto ctrl=ready(world);pickupCargo(ctrl,world,180);world.heroes[0].army[1].count=9;
  rejects([&]{ctrl.next(world,{});},"lost cargo silently recertified");
 }
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"evidence\":\"CPU synthetic controller tests only\",\"native_games\":0}\n";
}
