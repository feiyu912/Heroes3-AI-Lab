/* Isolated schema4 wire helpers. No engine state, RNG, shell or crypto-library dependency. */
#pragma once
#include <array>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace LabTypedPolicy
{
inline std::uint32_t rotateRight(std::uint32_t x, unsigned n) { return (x >> n) | (x << (32 - n)); }
inline std::string sha256(const std::string & raw)
{
 static constexpr std::array<std::uint32_t,64> k = {{
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2 }};
 std::array<std::uint32_t,8> h = {{0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19}};
 std::vector<std::uint8_t> bytes(raw.begin(), raw.end());
 const auto bits = static_cast<std::uint64_t>(bytes.size()) * 8;
 bytes.push_back(0x80);
 while(bytes.size() % 64 != 56) bytes.push_back(0);
 for(int shift = 56; shift >= 0; shift -= 8) bytes.push_back(static_cast<std::uint8_t>(bits >> shift));
 for(std::size_t start = 0; start < bytes.size(); start += 64)
 {
  std::array<std::uint32_t,64> w{};
  for(unsigned i = 0; i < 16; ++i)
   for(unsigned j = 0; j < 4; ++j) w[i] = (w[i] << 8) | bytes[start + 4 * i + j];
  for(unsigned i = 16; i < 64; ++i)
  {
   const auto s0 = rotateRight(w[i-15],7) ^ rotateRight(w[i-15],18) ^ (w[i-15] >> 3);
   const auto s1 = rotateRight(w[i-2],17) ^ rotateRight(w[i-2],19) ^ (w[i-2] >> 10);
   w[i] = w[i-16] + s0 + w[i-7] + s1;
  }
  auto a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],z=h[7];
  for(unsigned i = 0; i < 64; ++i)
  {
   const auto s1 = rotateRight(e,6) ^ rotateRight(e,11) ^ rotateRight(e,25);
   const auto t1 = z + s1 + ((e & f) ^ (~e & g)) + k[i] + w[i];
   const auto s0 = rotateRight(a,2) ^ rotateRight(a,13) ^ rotateRight(a,22);
   const auto t2 = s0 + ((a & b) ^ (a & c) ^ (b & c));
   z=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
  }
  h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=z;
 }
 std::ostringstream out;out << std::hex << std::setfill('0');
 for(auto word : h) out << std::setw(8) << word;
 return out.str();
}

// The exact response schema is flat and has only strings/nonnegative integers.
// Reject duplicate keys, booleans, decimal/exponent integers, nested objects,
// leading-zero numbers, unknown keys, trailing JSON and legacy plain integers.
struct Value { bool integer = false; std::uint64_t number = 0; std::string text; };
class FlatObjectParser
{
 const std::string & input;std::size_t at = 0;
 void spaces() { while(at<input.size() && (input[at]==' ' || input[at]=='\t' || input[at]=='\r' || input[at]=='\n')) ++at; }
 void take(char c) { spaces();if(at>=input.size() || input[at++]!=c) throw std::runtime_error("typed JSON syntax"); }
 unsigned hex(char c) const
 {
  if(c>='0' && c<='9') return c-'0';
  if(c>='a' && c<='f') return c-'a'+10;
  if(c>='A' && c<='F') return c-'A'+10;
  throw std::runtime_error("typed JSON unicode");
 }
 std::string string()
 {
  take('"');std::string result;
  while(at<input.size())
  {
   const unsigned char c=input[at++];
   if(c=='"') return result;
   if(c<32) throw std::runtime_error("typed JSON control");
   if(c!='\\') { result.push_back(static_cast<char>(c));continue; }
   if(at>=input.size()) throw std::runtime_error("typed JSON escape");
   switch(input[at++])
   {
    case '"':result+='"';break;case '\\':result+='\\';break;case '/':result+='/';break;
    case 'b':result+='\b';break;case 'f':result+='\f';break;case 'n':result+='\n';break;
    case 'r':result+='\r';break;case 't':result+='\t';break;
    case 'u':
    {
     if(at+4>input.size()) throw std::runtime_error("typed JSON unicode");
     unsigned code=0;for(int i=0;i<4;++i) code=16*code+hex(input[at++]);
     // All accepted keys/context strings are ASCII. No surrogate ambiguity.
     if(code>127) throw std::runtime_error("typed JSON non-ASCII context");
     result+=static_cast<char>(code);break;
    }
    default:throw std::runtime_error("typed JSON escape");
   }
  }
  throw std::runtime_error("typed JSON unterminated string");
 }
 Value value()
 {
  spaces();Value v;
  if(at<input.size() && input[at]=='"') { v.text=string();return v; }
  if(at>=input.size() || input[at]<'0' || input[at]>'9') throw std::runtime_error("typed JSON integer required");
  v.integer=true;const auto begin=at;
  while(at<input.size() && input[at]>='0' && input[at]<='9')
  {
   const auto digit=static_cast<unsigned>(input[at++]-'0');
   if(v.number>(std::numeric_limits<std::uint64_t>::max()-digit)/10) throw std::runtime_error("typed integer overflow");
   v.number=10*v.number+digit;
  }
  if(at-begin>1 && input[begin]=='0') throw std::runtime_error("typed leading zero");
  return v;
 }
public:
 explicit FlatObjectParser(const std::string & data):input(data) {}
 std::map<std::string,Value> parse()
 {
  if(input.empty() || input.size()>16384 || input.back()!='\n') throw std::runtime_error("typed JSON newline/size");
  take('{');std::map<std::string,Value> result;spaces();
  if(at<input.size() && input[at]=='}') throw std::runtime_error("typed JSON empty response");
  while(true)
  {
   const auto key=string();take(':');const auto v=value();
   if(!result.emplace(key,v).second) throw std::runtime_error("typed duplicate key");
   spaces();if(at>=input.size()) throw std::runtime_error("typed JSON incomplete");
   if(input[at]=='}') { ++at;break; }
   take(',');
  }
  spaces();if(at!=input.size()) throw std::runtime_error("typed trailing JSON");
  return result;
 }
};

struct Response { int index = -1; std::string op; std::string classification; };
inline Response parseResponse(const std::string & bytes, int decision, int player, int hero, int turn,
 const std::string & requestSHA, const std::vector<std::string> & operations,
 const std::string & responseSchema = "strategy-typed-action-response-v1")
{
 const auto object=FlatObjectParser(bytes).parse();
 const std::set<std::string> keys={"schema","selected_index","decision_id","player","hero","own_turn","op","request_sha256","classification"};
 if(object.size()!=keys.size()) throw std::runtime_error("typed response exact key set");
 for(const auto & entry:object) if(!keys.count(entry.first)) throw std::runtime_error("typed unknown key");
 const auto str=[&](const std::string & key)->const std::string &
 { const auto & v=object.at(key);if(v.integer) throw std::runtime_error("typed string required");return v.text; };
 const auto integer=[&](const std::string & key)->int
 { const auto & v=object.at(key);if(!v.integer || v.number>static_cast<std::uint64_t>(std::numeric_limits<int>::max())) throw std::runtime_error("typed integer range");return static_cast<int>(v.number); };
 if(str("schema")!=responseSchema || integer("decision_id")!=decision || decision<1 ||
    integer("player")!=player || integer("hero")!=hero || integer("own_turn")!=turn || turn<1)
  throw std::runtime_error("typed immutable response context");
 const auto index=integer("selected_index");
 if(index<0 || static_cast<std::size_t>(index)>=operations.size()) throw std::runtime_error("typed selected index");
 if(str("op")!=operations[index] || str("request_sha256")!=requestSHA || requestSHA.size()!=64)
  throw std::runtime_error("typed operation/request SHA");
 const auto & classification=str("classification");
 if(classification!="new_policy" && classification!="diagnostic_only") throw std::runtime_error("typed provenance");
 return {index,str("op"),classification};
}
}

// Bounded replan predicates use only published visible-state scalars.
#include <cmath>
namespace LabThreatReplan
{
inline bool pressure(int hx,int hy,int hz,double own,int tx,int ty,int tz,double enemy)
{
 if(hz!=tz || !std::isfinite(own) || !std::isfinite(enemy) || own<=0 || enemy<1.5*own) return false;
 const auto dx=static_cast<long long>(hx)-tx,dy=static_cast<long long>(hy)-ty;
 const auto ax=dx<0?-dx:dx,ay=dy<0?-dy:dy;
 return ax<=12 && ay<=12;
}
inline bool allowed(bool enabled,bool hasRetained,bool pressureNow,bool used,unsigned legalMoves)
{ return enabled && hasRetained && pressureNow && !used && legalMoves>1; }
}

// Pure schema5 helpers; original schema4 helpers above retain their defaults.
#include <cstdlib>
#include <fstream>
namespace LabLearnedBuild
{
inline bool enabled(const char * mode)
{
 if(!mode || std::string(mode).empty()) return false;
 if(std::string(mode)!="build_v1") throw std::runtime_error("unknown learned build mode");
 return true;
}
struct Window
{
 int ownTurn=0; bool open=false;
 void begin(int turn)
 {
  if(turn<1 || turn<=ownTurn) throw std::runtime_error("nonmonotonic build turn");
  ownTurn=turn;open=true;
 }
 bool select(const std::string & op)
 {
  if(ownTurn<1) return false;
  if(op!="move" && op!="end_turn" && op!="build") return false;
  if(op=="build" && !open) return false;
  open=false;return true;
 }
};
template<class Resources> inline std::string resources(const Resources & values)
{
 const char * names[]={"wood","mercury","ore","sulfur","crystal","gems","gold"};
 std::ostringstream out;out << '{';
 for(unsigned i=0;i<7;++i) { if(i) out << ',';out << '"' << names[i] << "\":" << values[i]; }
 out << '}';return out.str(); // Received relative SetResources may legitimately be negative.
}
template<class Resources> inline bool nonnegative(const Resources & values)
{ for(unsigned i=0;i<7;++i) if(values[i]<0) return false;return true; }
template<class IDs> inline std::string ids(const IDs & values)
{
 std::ostringstream out;out << '[';bool first=true;
 for(const auto & id:values) { if(!first) out << ',';first=false;out << id.getNum(); }
 out << ']';return out.str();
}
template<class Logger> inline void mirrorPack(const std::string & json, Logger log)
{
 log(json);
 const auto * path=std::getenv("LAB_ADV_BUILD_PACKS");
 const auto * agent=std::getenv("LAB_ADV_AGENT_DIR");
 if(!path && !agent) return;
 std::ofstream out(path ? std::string(path) : std::string(agent)+"/build-packs.jsonl",std::ios::app|std::ios::binary);
 const auto line=json+'\n';if(out) out.write(line.data(),line.size());
}
}

#include <algorithm>
// New independent schema6 mode. Legacy schema4/5 parsers/windows are untouched.
namespace LabLearnedRecruit
{
inline std::string jsonString(const std::string & value)
{
 std::ostringstream out;out << '"';
 for(const unsigned char c:value)
 {
  if(c=='"' || c=='\\') out << '\\' << static_cast<char>(c);
  else if(c<32) out << "\\u" << std::hex << std::setfill('0') << std::setw(4) << static_cast<unsigned>(c) << std::dec;
  else out << static_cast<char>(c);
 }
 out << '"';return out.str();
}
inline bool enabled(const char * mode) { return mode && std::string(mode)=="build_recruit_v1"; }
template<class Window> inline bool select(Window & window,const std::string & op)
{
 if(window.ownTurn<1) return false;
 if(op=="build" || op=="recruit") return window.open;
 if(op=="move") return true; // Owned-town economy remains available after real movement.
 if(op!="end_turn") return false;
 window.open=false;return true;
}
inline std::set<int> quantities(int affordableAvailable)
{
 if(affordableAvailable<=0) return {};
 return {1,std::max(1,affordableAvailable/2),affordableAvailable};
}
}
