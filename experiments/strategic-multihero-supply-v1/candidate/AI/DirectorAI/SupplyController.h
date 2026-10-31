#pragma once
// scripted_supply-v1: deterministic research controller, no learned transitions.
// Inputs are owned state only. The adapter alone may issue native requests.
#include <algorithm>
#include <array>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

namespace supply_v1
{
struct Pos { int x=-1,y=-1,z=-1; bool operator==(const Pos &p) const { return x==p.x && y==p.y && z==p.z; } };
struct Stack { int creature=-1; long long count=0; bool operator==(const Stack &s) const { return creature==s.creature && count==s.count; } };
using Army=std::array<Stack,7>;
struct Hero { int id=-1,movement=0; bool garrison=false,boat=false; Pos pos; Army army; };
struct Town { int id=-1,visitor=-1; Pos pos; Army army; };
struct World { std::vector<Hero> heroes; std::vector<Town> towns; };
enum class Phase { Return, Pickup, Meeting, Exchange };
enum class Op { Move, Transfer, Close, End };
struct Command
{
 Op op=Op::Move; int actor=-1,target=-1,source=-1,from=-1,to=-1,query=-1;
 Pos destination; bool delivery=false; Army donorBefore{},recipientBefore{};
};
// NewTurn may precede the ACK of the previous EndTurn. Preserve that immutable
// request and delay beginTurn; the old ACK must never end the newly started turn.
class TurnBoundaryGate
{
 std::optional<int> queued;
public:
 bool defer(bool endPending,int query)
 {
  if(queued) throw std::runtime_error("duplicate_queued_own_turn");
  if(!endPending) return false;
  queued=query;return true;
 }
 std::optional<int> afterEndAck() {auto q=queued;queued.reset();return q;}
 bool waiting() const {return queued.has_value();}
};
inline int occupied(const Army&a) { return std::count_if(a.begin(),a.end(),[](const Stack&s){return s.count>0;}); }
inline int compatible(const Army&a,int creature)
{
 for(int i=0;i<7;++i) if(a[i].count>0 && a[i].creature==creature) return i;
 for(int i=0;i<7;++i) if(a[i].count==0) return i;
 return -1;
}
inline std::map<int,long long> totals(const Army&a)
{ std::map<int,long long> out;for(const auto&s:a) if(s.count>0) out[s.creature]+=s.count;return out; }
class Controller
{
public:
 int main=-1,courier=-1,home=-1,turn=0,cursor=0,cycles=0;
 Phase phase=Phase::Return;
 Phase phaseBeforeExchange=Phase::Return;
 bool exchangeDelivery=false;
 std::map<int,int> spent;
 std::map<int,std::string> blocked;
 std::map<int,Pos> goals;
 std::optional<Command> pending;
 int request=-1,query=-1;
 bool failed=false;
 std::string failure;
 static constexpr int budget=48;

 void require(bool ok,const std::string &why)
 { if(!ok) {failed=true;failure=why;throw std::runtime_error(why);} }
 const Hero &hero(const World&w,int id) const
 { auto it=std::find_if(w.heroes.begin(),w.heroes.end(),[&](const Hero&h){return h.id==id;});if(it==w.heroes.end()) throw std::runtime_error("role_missing");return *it; }
 const Town &town(const World&w) const
 { auto it=std::find_if(w.towns.begin(),w.towns.end(),[&](const Town&t){return t.id==home;});if(it==w.towns.end()) throw std::runtime_error("home_missing");return *it; }
 void validate(const World&w)
 {
  require(w.heroes.size()==2,"exactly_two_owned_required");
  require(w.heroes[0].id!=w.heroes[1].id,"duplicate_hero_id");
  require(main!=courier && main>=0 && courier>=0,"invalid_roles");
  try { (void)hero(w,main);(void)hero(w,courier);(void)town(w); }
  catch(const std::exception&e) { require(false,e.what()); }
  for(const auto&h:w.heroes) for(const auto&s:h.army) require(s.count>=0 && (s.count==0 || s.creature>=0),"bad_army");
 }
 void start(const World&w)
 {
  require(main<0 && courier<0,"roles_already_initialized");
  require(w.heroes.size()==2 && !w.towns.empty(),"two_heroes_and_owned_town_required");
  main=std::min(w.heroes[0].id,w.heroes[1].id);courier=std::max(w.heroes[0].id,w.heroes[1].id);
  home=std::min_element(w.towns.begin(),w.towns.end(),[](const Town&a,const Town&b){return a.id<b.id;})->id;
  validate(w);
 }
 void beginTurn(const World&w)
 {
  require(!pending && query<0,"turn_started_with_live_transaction");validate(w);
  ++turn;spent.clear();blocked.clear(); // roles, goals, home, phase and cycles survive own turns.
 }
 bool eligible(const Hero&h) const
 { auto s=spent.find(h.id);return h.movement>0 && !h.garrison && !h.boat && !blocked.count(h.id) && (s==spent.end() || s->second<budget); }
 void yield(int actor,const std::string&why) { require(actor==main || actor==courier,"unknown_yield_actor");blocked[actor]=why; }
 void exchangeStarted(int a,int b,int q)
 {
  require(query<0 && q>=0 && ((a==main && b==courier)||(a==courier && b==main)),"unexpected_exchange");
  phaseBeforeExchange=phase;
  exchangeDelivery=phase==Phase::Meeting && pending && pending->op==Op::Move && pending->actor==courier && pending->target==main;
  // TryMoveHero with zero displacement may arrive before ExchangeDialog. The
  // genuine dialog proves a successful interaction; only that provisional
  // blocked reason is removed, without resetting the actor's request budget.
  if(pending && pending->op==Op::Move)
  {
   auto reason=blocked.find(pending->actor);
   if(reason!=blocked.end() && reason->second=="no_displacement_without_exchange") blocked.erase(reason);
  }
  query=q;phase=Phase::Exchange;
 }
 std::optional<Command> transfer(const Army&donor,const Army&recipient,int source,int target,bool delivery)
 {
  if(delivery && occupied(donor)<2) return {};
  for(int i=0;i<7;++i) if(donor[i].count>0)
  {
   int slot=compatible(recipient,donor[i].creature);if(slot<0) continue;
   Command c;c.op=Op::Transfer;c.actor=courier;c.source=source;c.target=target;c.from=i;c.to=slot;
   c.query=query;c.delivery=delivery;c.donorBefore=donor;c.recipientBefore=recipient;return c;
  }
  return {};
 }
 // mainGoal comes from a deterministic visible/pathfinder adapter. It never uses schema4.
 std::optional<Command> next(const World&w,const std::optional<Pos>&mainGoal)
 {
  require(!failed,"controller_failed");validate(w);if(pending) return {};
  const auto&c=hero(w,courier);const auto&m=hero(w,main);const auto&t=town(w);
  if(query>=0)
  {
   require(phase==Phase::Exchange,"query_phase_mismatch");
   if(exchangeDelivery) {auto cmd=transfer(c.army,m.army,courier,main,true);if(cmd) return cmd;}
   Command close;close.op=Op::Close;close.query=query;return close;
  }
  for(int attempt=0;attempt<2;++attempt)
  {
   int id=cursor==0?main:courier;cursor=1-cursor;const auto&h=hero(w,id);
   if(!eligible(h)) continue;
   Command cmd;cmd.actor=id;cmd.op=Op::Move;
   if(id==main)
   {
    if(!mainGoal) { yield(id,"no_main_goal");continue; }
    cmd.destination=*mainGoal;
   }
   else
   {
    if(phase==Phase::Return && t.visitor==courier) phase=Phase::Pickup;
    if(phase==Phase::Pickup)
    {
     require(t.visitor==courier,"pickup_requires_actual_town_visitor");
     auto pickup=transfer(t.army,c.army,home,courier,false);
     if(pickup) return pickup;
     if(occupied(c.army)<2) { yield(id,"no_deliverable_cargo_preserving_reserve");continue; }
     phase=Phase::Meeting;
    }
    if(phase==Phase::Meeting) {cmd.target=main;cmd.destination=m.pos;}
    else {cmd.target=home;cmd.destination=t.pos;}
   }
   if(cmd.destination==h.pos) { yield(id,"same_tile_without_real_exchange");continue; }
   goals[id]=cmd.destination;return cmd;
  }
  Command end;end.op=Op::End;return end;
 }
 void prepare(const Command&c)
 {
  require(!pending && request<0,"second_global_pending_request");pending=c;
  if(c.actor>=0) ++spent[c.actor];
 }
 void bind(int id,Op actual)
 { require(pending && request<0 && id>0 && pending->op==actual,"bad_native_request_binding");request=id; }
 // Only real PackageApplied calls this method; it never invents an ACK.
 void ack(int id,Op actual,bool success,const World&w)
 {
  require(pending && request==id && pending->op==actual,"unmatched_native_ack");
  require(success,"native_request_rejected");const Command c=*pending;
  if(c.op==Op::Transfer)
  {
   const Army &donor=c.delivery?hero(w,courier).army:town(w).army;
   const Army &recipient=c.delivery?hero(w,main).army:hero(w,courier).army;
   auto expectedDonor=c.donorBefore,expectedRecipient=c.recipientBefore;
   const auto stack=expectedDonor[c.from];
   require(stack.count>0 && (expectedRecipient[c.to].count==0 || expectedRecipient[c.to].creature==stack.creature),"unsafe_transfer");
   expectedDonor[c.from]=Stack{};expectedRecipient[c.to].creature=stack.creature;expectedRecipient[c.to].count+=stack.count;
   // Empty native slots may carry a stale creature identifier; compare nonempty totals and slots.
   for(int i=0;i<7;++i)
   {
    require(donor[i].count==expectedDonor[i].count && (!donor[i].count || donor[i].creature==expectedDonor[i].creature),"donor_delta_mismatch");
    require(recipient[i].count==expectedRecipient[i].count && (!recipient[i].count || recipient[i].creature==expectedRecipient[i].creature),"recipient_delta_mismatch");
   }
   if(c.delivery) require(occupied(donor)>=1,"courier_reserve_lost");
  }
  if(c.op==Op::Close)
  {
   require(c.query==query,"close_query_mismatch");query=-1;
   if(exchangeDelivery) {phase=Phase::Return;++cycles;}
   else phase=phaseBeforeExchange; // legal accidental meeting: close only, no delivery/cycle claim.
   exchangeDelivery=false;
  }
  pending.reset();request=-1;
 }
 bool boundary(bool movement,bool battle,bool nativeQueries,bool ownedRequests) const
 { return !failed && !pending && request<0 && query<0 && !movement && !battle && !nativeQueries && !ownedRequests; }
};
}
