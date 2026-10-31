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
 check(transfers==2 && occupied(w.heroes[0].army)==1,"donor retains last stack");
 check(w.heroes[1].army[0].count==15 && w.heroes[1].army[1].count==3,"compatible merge and empty slot transfers");
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
 {auto world=fixture();auto ctrl=ready(world);ctrl.phase=Phase::Exchange;ctrl.query=4;world.heroes[0].army[1]=Stack{};
  ctrl.exchangeDelivery=true;
  auto cmd=ctrl.next(world,{});check(cmd && cmd->op==Op::Close,"one donor stack never transferred");}
 {auto world=fixture();auto ctrl=ready(world);ctrl.phase=Phase::Pickup;world.towns[0].visitor=-1;ctrl.cursor=1;
  rejects([&]{ctrl.next(world,{});},"remote pickup accepted");}
 {auto world=fixture();auto ctrl=ready(world);ctrl.cursor=1;world.towns[0].visitor=-1;
  auto cmd=ctrl.next(world,{});check(cmd && cmd->op==Op::End,"same position is not fake native interaction");}
 std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"evidence\":\"CPU synthetic controller tests only\",\"native_games\":0}\n";
}
