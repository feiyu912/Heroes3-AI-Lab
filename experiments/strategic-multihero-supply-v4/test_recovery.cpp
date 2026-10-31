#include "SupplyRecovery.h"
#include <functional>
#include <iostream>
using namespace supply_recovery_v4;
int checks=0;
void check(bool yes,const char*why){++checks;ensure(yes,why);}
void reject(const std::function<void()>&f){try{f();}catch(const std::runtime_error&){++checks;return;}throw std::runtime_error("negative_recovery_case_accepted");}
Snapshot fixture()
{
 Snapshot s;s.source=std::string(64,'a');s.nonce="synthetic-cpu-v4";s.player=0;s.day=2;s.economy="synthetic economy 5000 10 10";
 supply_v1::Hero main;main.id=0;main.movement=1500;main.pos={9,1,0};main.army[0]={0,5};
 supply_v1::Hero courier;courier.id=2;courier.movement=1500;courier.pos={6,8,0};courier.army[0]={2,3};
 supply_v1::Town town;town.id=3;town.visitor=2;town.pos=courier.pos;town.army[0]={0,10};
 s.world.heroes={main,courier};s.world.towns={town};auto&c=s.control;c.start(s.world);c.beginTurn(s.world);c.cursor=1;
 auto p=c.next(s.world,supply_v1::Pos{9,2,0});ensure(bool(p)&&p->op==supply_v1::Op::Transfer,"synthetic_pickup_missing");
 c.prepare(*p);c.bind(8,supply_v1::Op::Transfer);s.world.towns[0].army[0]=supply_v1::Stack{};s.world.heroes[1].army[1]={0,10};
 c.ack(8,supply_v1::Op::Transfer,true,s.world);c.cursor=1;(void)c.next(s.world,supply_v1::Pos{9,2,0});
 c.beginTurn(s.world);c.cursor=0;auto m=c.next(s.world,supply_v1::Pos{9,2,0});c.prepare(*m);c.bind(9,supply_v1::Op::Move);
 s.world.heroes[0].pos={9,2,0};c.ack(9,supply_v1::Op::Move,true,s.world);s.visited.insert({9,2,0});return s;
}
int main(int argc,char**argv)
{
 try
 {
  if(argc==3&&std::string(argv[1])=="sha"){std::cout<<sha256(readFile(argv[2]));return 0;}
  if(argc==3&&std::string(argv[1])=="decode"){std::cout<<encode(decode(readFile(argv[2],8*1024*1024)));return 0;}
  auto s=fixture();if(argc==2&&std::string(argv[1])=="fixture"){std::cout<<encode(s);return 0;}
  check(sha256("")=="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","sha_empty");
  check(sha256("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad","sha_abc");
  check(sha256(std::string(1000000,'a'))=="cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0","sha_million_a");
  const auto text=encode(s);const auto restored=decode(text);
  check(text==encode(restored),"nontrivial_roundtrip");check(nontrivial(restored,2),"checkpoint_nontrivial");
  check(restored.control.turn==2&&restored.control.spent.at(0)==1&&restored.control.cursor==1,"restore_turn_budget_cursor");
  check(restored.control.cargo.at(0)==10&&restored.control.reserve.at(2)==3&&restored.control.cargoSlots[1].count==10,"restore_cargo_slot_provenance");
  check(restored.visited==s.visited&&restored.control.goals.at(0)==s.control.goals.at(0),"restore_navigation_state");
  check(worldText(restored.world,restored.economy)==worldText(s.world,s.economy),"restore_world_economy");
  reject([&]{decode(text+"garbage");});reject([&]{decode(text.substr(0,text.size()/2));});reject([&]{decode("old-epoch\n"+text);});
  auto bad=s;bad.control.pending=supply_v1::Command{};reject([&]{encode(bad);});
  bad=s;bad.control.query=7;reject([&]{encode(bad);});
  auto invalid=[&](const std::function<void(Snapshot&)>&mutate){auto b=s;mutate(b);reject([&]{decode(encode(b));});};
  invalid([](Snapshot&b){b.control.cursor=2;});invalid([](Snapshot&b){b.control.spent[0]=55;});
  invalid([](Snapshot&b){b.control.goals[0].x=-1;});invalid([](Snapshot&b){b.visited.insert({-1,0,0});});
  invalid([](Snapshot&b){b.control.initialReserve[6].count=-1;});invalid([](Snapshot&b){b.control.cargoSlots[6].count=-1;});
  invalid([](Snapshot&b){b.control.cargoSlots[1].count=9;});invalid([](Snapshot&b){b.control.picked[0]=11;});
  invalid([](Snapshot&b){b.world.heroes[1].army[0].count=2;});invalid([](Snapshot&b){b.world.heroes[1].army[1].count=9;});
  invalid([](Snapshot&b){b.world.heroes[0].id=2;});invalid([](Snapshot&b){b.control.blocked[99]="foreign";});
  invalid([](Snapshot&b){b.source=std::string(64,'z');});invalid([](Snapshot&b){b.control.goals[99]={1,1,0};});
  bad=s;bad.control.turn=1;check(!nontrivial(bad,2),"reject_day_one_as_target");
  bad=s;bad.control.spent.clear();check(!nontrivial(bad,2),"reject_empty_turn_budget");
  bad=s;bad.visited.clear();check(!nontrivial(bad,2),"reject_empty_navigation");
  std::cout<<"{\"passed\":true,\"checks\":"<<checks<<",\"scope\":\"synthetic C++ codec/SHA/controller boundary only\",\"native_games\":0}\n";
 }
 catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
