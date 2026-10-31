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
