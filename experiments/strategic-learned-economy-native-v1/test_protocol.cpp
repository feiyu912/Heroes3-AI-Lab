#include "candidate/AI/DirectorAI/TypedPolicyProtocol.h"
#include <cassert>
#include <iostream>
#include <array>
template<class Function> void rejected(Function function)
{ bool failed=false;try { function(); } catch(const std::exception &) {failed=true;} assert(failed); }
int main()
{
 using namespace LabLearnedBuild;
 assert(!enabled(nullptr));assert(!enabled(""));assert(enabled("build_v1"));rejected([]{enabled("on");});
 Window window;assert(!window.select("build"));assert(!window.select("move"));
 window.begin(1);assert(window.open);assert(window.select("build"));assert(!window.open);assert(!window.select("build"));assert(window.select("move"));
 window.begin(2);assert(window.select("move"));assert(!window.select("build"));
 window.begin(3);assert(window.select("end_turn"));assert(!window.select("build"));
 rejected([&]{window.begin(3);});rejected([&]{window.begin(-1);});
 window.begin(4);assert(!window.select("hire"));assert(window.open);
 std::array<long long,7> values={{3,5,7,11,13,17,19}};
 assert(resources(values)=="{\"wood\":3,\"mercury\":5,\"ore\":7,\"sulfur\":11,\"crystal\":13,\"gems\":17,\"gold\":19}");
 assert(nonnegative(values));values[1]=-5;assert(!nonnegative(values));assert(resources(values).find("\"mercury\":-5")!=std::string::npos);
 const std::string hash(64,'a');
 const std::string response="{\"schema\":\"strategy-typed-action-response-v2\",\"selected_index\":1,\"decision_id\":7,\"player\":1,\"hero\":23,\"own_turn\":4,\"op\":\"build\",\"request_sha256\":\""+hash+"\",\"classification\":\"new_policy\"}\n";
 const std::vector<std::string> ops={"move","build","end_turn"};
 const auto parsed=LabTypedPolicy::parseResponse(response,7,1,23,4,hash,ops,"strategy-typed-action-response-v2");assert(parsed.index==1 && parsed.op=="build");
 rejected([&]{LabTypedPolicy::parseResponse(response,7,1,23,4,hash,ops);});
 rejected([&]{LabTypedPolicy::parseResponse(response,7,1,99,4,hash,ops,"strategy-typed-action-response-v2");});
 rejected([&]{LabTypedPolicy::parseResponse(response,7,1,23,5,hash,ops,"strategy-typed-action-response-v2");});
 rejected([&]{LabTypedPolicy::parseResponse(response,7,1,23,4,std::string(64,'b'),ops,"strategy-typed-action-response-v2");});
 rejected([&]{LabTypedPolicy::parseResponse(response,7,1,23,4,hash,{"move","move","end_turn"},"strategy-typed-action-response-v2");});
 std::string duplicate=response;duplicate.insert(1,"\"player\":1,");
 rejected([&]{LabTypedPolicy::parseResponse(duplicate,7,1,23,4,hash,ops,"strategy-typed-action-response-v2");});
 std::string legacy=response;legacy.replace(legacy.find("response-v2"),11,"response-v1");
 rejected([&]{LabTypedPolicy::parseResponse(legacy,7,1,23,4,hash,ops,"strategy-typed-action-response-v2");});
 std::cout << "{\"passed\":true,\"scope\":\"pure wire/window CPU unit tests only\",\"native_games\":0}\n";
}
