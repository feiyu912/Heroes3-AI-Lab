#pragma once
#include "SupplyController.h"
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <set>
#include <sstream>
#include <tuple>

namespace supply_recovery_v4
{
inline constexpr const char* sourceToken="@COMPILED_SOURCE_TOKEN@";
inline constexpr const char* epoch="supply-native-boundary-v4";
inline void ensure(bool yes,const char*reason) {if(!yes)throw std::runtime_error(reason);}
inline std::string sha256(const std::string&data)
{
 static const uint32_t k[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
 0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,
 0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,
 0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,
 0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
 0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,
 0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
 auto rr=[](uint32_t x,int n){return (x>>n)|(x<<(32-n));};
 std::vector<unsigned char>bytes(data.begin(),data.end());uint64_t bits=uint64_t(bytes.size())*8;bytes.push_back(128);
 while(bytes.size()%64!=56)bytes.push_back(0);
 for(int i=7;i>=0;--i)bytes.push_back(static_cast<unsigned char>(bits>>(i*8)));
 uint32_t h[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
 for(size_t offset=0;offset<bytes.size();offset+=64)
 {
  uint32_t w[64];for(int i=0;i<16;++i)w[i]=(uint32_t(bytes[offset+4*i])<<24)|(uint32_t(bytes[offset+4*i+1])<<16)|(uint32_t(bytes[offset+4*i+2])<<8)|bytes[offset+4*i+3];
  for(int i=16;i<64;++i)w[i]=w[i-16]+(rr(w[i-15],7)^rr(w[i-15],18)^(w[i-15]>>3))+w[i-7]+(rr(w[i-2],17)^rr(w[i-2],19)^(w[i-2]>>10));
  uint32_t a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],q=h[7];
  for(int i=0;i<64;++i){uint32_t t=q+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^((~e)&g))+k[i]+w[i];uint32_t u=(rr(a,2)^rr(a,13)^rr(a,22))+((a&b)^(a&c)^(b&c));q=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+u;}
  h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=q;
 }
 std::ostringstream out;out<<std::hex<<std::setfill('0');for(auto value:h)out<<std::setw(8)<<value;return out.str();
}
inline std::string readFile(const std::string&path,size_t limit=128*1024*1024)
{
 std::ifstream in(path,std::ios::binary);ensure(bool(in),"recovery_file_missing");
 in.seekg(0,std::ios::end);auto length=in.tellg();ensure(length>=0 && static_cast<uint64_t>(length)<=limit,"recovery_file_size");
 std::string data(static_cast<size_t>(length),'\0');in.seekg(0);if(!data.empty())in.read(&data[0],data.size());ensure(bool(in),"recovery_file_read");return data;
}
using supply_v1::Army;using supply_v1::World;using supply_v1::Pos;
struct Snapshot
{
 supply_v1::Controller control;
 std::set<std::tuple<int,int,int>> visited;
 World world;
 std::string source,nonce,economy;
 int player=-1,day=0;
};
inline void putArmy(std::ostream&out,const Army&a) {for(const auto&s:a)out<<s.creature<<' '<<s.count<<' ';out<<'\n';}
inline void getArmy(std::istream&in,Army&a) {for(auto&s:a)in>>s.creature>>s.count;}
inline size_t size(std::istream&in,size_t max)
{long long n=-1;in>>n;ensure(bool(in)&&n>=0&&static_cast<uint64_t>(n)<=max,"recovery_collection_size");return size_t(n);}
template<class T>void putMap(std::ostream&out,const std::map<int,T>&m)
{out<<m.size()<<' ';for(const auto&p:m)out<<p.first<<' '<<p.second<<' ';out<<'\n';}
template<class T>void getMap(std::istream&in,std::map<int,T>&m)
{for(size_t n=size(in,1024);n;--n){int k;T v;in>>k>>v;ensure(bool(in)&&m.emplace(k,v).second,"recovery_duplicate_or_bad_map");}}
inline std::string worldText(const World&w,const std::string&economy)
{
 std::ostringstream out;out<<w.heroes.size()<<'\n';
 for(const auto&h:w.heroes){out<<h.id<<' '<<h.movement<<' '<<h.garrison<<' '<<h.boat<<' '<<h.pos.x<<' '<<h.pos.y<<' '<<h.pos.z<<'\n';putArmy(out,h.army);}
 out<<w.towns.size()<<'\n';for(const auto&t:w.towns){out<<t.id<<' '<<t.visitor<<' '<<t.pos.x<<' '<<t.pos.y<<' '<<t.pos.z<<'\n';putArmy(out,t.army);}
 out<<std::quoted(economy)<<'\n';return out.str();
}
inline std::string encode(const Snapshot&s)
{
 const auto&c=s.control;ensure(c.boundary(false,false,false,false)&&!c.exchangeDelivery,"recovery_live_control");
 std::ostringstream out;out<<epoch<<'\n'<<std::quoted(s.source)<<' '<<std::quoted(s.nonce)<<' '<<s.player<<' '<<s.day<<'\n';
 out<<c.main<<' '<<c.courier<<' '<<c.home<<' '<<c.turn<<' '<<c.cursor<<' '<<c.cycles<<' '<<int(c.phase)<<' '<<int(c.phaseBeforeExchange)<<' '
 <<c.job<<' '<<c.successfulJobs<<' '<<c.incompleteAttempts<<' '<<int(c.jobStatus)<<' '<<std::quoted(c.deliveryReason)<<'\n';
 putArmy(out,c.initialReserve);putArmy(out,c.cargoSlots);putMap(out,c.reserve);putMap(out,c.cargo);putMap(out,c.picked);putMap(out,c.delivered);putMap(out,c.spent);
 out<<c.blocked.size()<<' ';for(const auto&p:c.blocked)out<<p.first<<' '<<std::quoted(p.second)<<' ';out<<'\n';
 out<<c.goals.size()<<' ';for(const auto&p:c.goals)out<<p.first<<' '<<p.second.x<<' '<<p.second.y<<' '<<p.second.z<<' ';out<<'\n';
 out<<s.visited.size()<<' ';for(const auto&p:s.visited)out<<std::get<0>(p)<<' '<<std::get<1>(p)<<' '<<std::get<2>(p)<<' ';out<<'\n';
 out<<worldText(s.world,s.economy);return out.str();
}
inline Snapshot decode(const std::string&text)
{
 ensure(text.size()<=8*1024*1024,"recovery_control_too_large");Snapshot s;auto&c=s.control;std::istringstream in(text);std::string tag;in>>tag;ensure(tag==epoch,"recovery_epoch_mismatch");
 in>>std::quoted(s.source)>>std::quoted(s.nonce)>>s.player>>s.day;
 int phase=-1,before=-1,status=-1;
 in>>c.main>>c.courier>>c.home>>c.turn>>c.cursor>>c.cycles>>phase>>before>>c.job>>c.successfulJobs>>c.incompleteAttempts>>status>>std::quoted(c.deliveryReason);
 ensure(phase>=0&&phase<3&&before>=0&&before<3&&status>=0&&status<=3,"recovery_invalid_phase");
 c.phase=supply_v1::Phase(phase);c.phaseBeforeExchange=supply_v1::Phase(before);c.jobStatus=supply_v1::JobStatus(status);
 getArmy(in,c.initialReserve);getArmy(in,c.cargoSlots);getMap(in,c.reserve);getMap(in,c.cargo);getMap(in,c.picked);getMap(in,c.delivered);getMap(in,c.spent);
 for(size_t n=size(in,2);n;--n){int id;std::string why;in>>id>>std::quoted(why);ensure(c.blocked.emplace(id,why).second,"recovery_duplicate_blocked");}
 for(size_t n=size(in,2);n;--n){int id;Pos p;in>>id>>p.x>>p.y>>p.z;ensure(c.goals.emplace(id,p).second,"recovery_duplicate_goal");}
 for(size_t n=size(in,65536);n;--n){int x,y,z;in>>x>>y>>z;ensure(s.visited.emplace(x,y,z).second,"recovery_duplicate_visited");}
 for(size_t n=size(in,2);n;--n){supply_v1::Hero h;in>>h.id>>h.movement>>h.garrison>>h.boat>>h.pos.x>>h.pos.y>>h.pos.z;getArmy(in,h.army);s.world.heroes.push_back(h);}
 for(size_t n=size(in,128);n;--n){supply_v1::Town t;in>>t.id>>t.visitor>>t.pos.x>>t.pos.y>>t.pos.z;getArmy(in,t.army);s.world.towns.push_back(t);}
 in>>std::quoted(s.economy);ensure(bool(in),"recovery_truncated_control");in>>std::ws;ensure(in.eof(),"recovery_trailing_data");
 ensure(s.player>=0&&s.player<8&&s.day>0&&c.turn>0&&c.cursor>=0&&c.cursor<2&&c.cycles>=0&&c.job>=0&&c.successfulJobs>=0&&c.incompleteAttempts>=0,"recovery_invalid_counter");
 ensure(s.source.size()==64&&!s.nonce.empty()&&s.nonce.size()<=96,"recovery_identity_missing");
 ensure(std::all_of(s.source.begin(),s.source.end(),[](char ch){return(ch>='0'&&ch<='9')||(ch>='a'&&ch<='f');}),"recovery_invalid_source_digest");
 for(const auto*army:{&c.initialReserve,&c.cargoSlots})for(const auto&stack:*army)
  ensure(stack.count>=0&&(stack.count==0||stack.creature>=0),"recovery_invalid_persisted_army");
 for(const auto&p:c.goals)ensure(p.second.x>=0&&p.second.y>=0&&p.second.z>=0,"recovery_negative_goal");
 for(const auto&p:s.visited)ensure(std::get<0>(p)>=0&&std::get<1>(p)>=0&&std::get<2>(p)>=0,"recovery_negative_visited");
 for(const auto&h:s.world.heroes)ensure(h.movement>=0&&h.pos.x>=0&&h.pos.y>=0&&h.pos.z>=0,"recovery_bad_world_hero");
 for(const auto&t:s.world.towns)ensure(t.pos.x>=0&&t.pos.y>=0&&t.pos.z>=0,"recovery_bad_world_town");
 for(const auto&p:c.spent)ensure((p.first==c.main||p.first==c.courier)&&p.second>=0&&p.second<=54,"recovery_invalid_budget");
 for(const auto&p:c.blocked)ensure(p.first==c.main||p.first==c.courier,"recovery_invalid_actor");
 for(const auto&p:c.goals)ensure(p.first==c.main||p.first==c.courier,"recovery_invalid_goal_actor");
 ensure(c.reserve==supply_v1::totals(c.initialReserve)&&!c.reserve.empty(),"recovery_reserve_mismatch");
 auto sum=c.cargo;for(const auto&p:c.delivered)sum[p.first]+=p.second;ensure(sum==c.picked,"recovery_cargo_ledger_mismatch");
 for(const auto*map:{&c.reserve,&c.cargo,&c.picked,&c.delivered})for(const auto&p:*map)ensure(p.first>=0&&p.second>0,"recovery_invalid_cargo_count");
 c.validate(s.world);ensure(encode(s)==text,"recovery_noncanonical_encoding");return s;
}
inline bool nontrivial(const Snapshot&s,int targetTurn)
{
 const auto&c=s.control;int used=0;for(const auto&p:c.spent)used+=p.second;
 return c.turn==targetTurn&&used>0&&c.jobStatus==supply_v1::JobStatus::Carrying&&!c.cargo.empty()&&c.delivered.empty()&&c.cargo==c.picked&&c.phase==supply_v1::Phase::Meeting&&!s.visited.empty();
}
}
