"""Compile the exact candidate dispatch fragment against an immediate-transport test double."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;candidate=HERE/'candidate/client/Client.cpp';text=candidate.read_text()
start=text.index('\twaitingRequest.pushBack(requestID);',text.index('int CClient::sendRequest('))
end=text.index('\n\tif(waitTillRealize)',start);fragment=text[start:end]
source=r'''
#include <cassert>
#include <map>
#include <memory>
#include <string>
#include <vector>
#include <stdexcept>
std::vector<std::string> order;
struct Request{mutable int requestID=-1,player=-1;};
struct Interface{std::string dllName;int calls=0;bool fail=false;void requestSent(const Request*p,int id){assert(p->requestID==id);++calls;order.push_back("bind");if(fail)throw std::runtime_error("observer failure");}};
struct Waiting{std::vector<int> ids;void pushBack(int id){ids.push_back(id);}}waitingRequest;
struct Server{void sendGamePack(const Request&r){assert(!waitingRequest.ids.empty() && waitingRequest.ids.back()==r.requestID);order.push_back("apply-immediately");}};
struct Game{Server s;Server&server(){return s;}}game;Game*GAME=&game;
void run(std::map<int,std::shared_ptr<Interface>>&playerint){Request request;int requestID=17,player=0;
FRAGMENT
}
int main(){
 for(const auto& name:std::vector<std::string>{"DirectorAI","Nullkiller2","MMAI"}){
  order.clear();auto receiver=std::make_shared<Interface>();receiver->dllName=name;std::map<int,std::shared_ptr<Interface>> interfaces{{0,receiver}};run(interfaces);
  assert(receiver->calls==1 && order.size()==2);
  assert(order[0]==(name=="DirectorAI"?"bind":"apply-immediately"));
 }
 order.clear();std::map<int,std::shared_ptr<Interface>> absent;run(absent);assert(order.size()==1 && order[0]=="apply-immediately");
 order.clear();auto receiver=std::make_shared<Interface>();receiver->dllName="DirectorAI";receiver->fail=true;std::map<int,std::shared_ptr<Interface>> failing{{0,receiver}};
 try{run(failing);assert(false);}catch(const std::runtime_error&){}assert(order.size()==1 && order[0]=="bind");
}
'''.replace('FRAGMENT',fragment)
with tempfile.TemporaryDirectory(prefix='request-dispatch-cpp-') as tmp:
    root=Path(tmp);p=root/'test.cpp';p.write_text(source)
    r=subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-O2',str(p),'-o',str(root/'test')],capture_output=True,text=True);assert r.returncode==0,r.stderr
    assert subprocess.run([str(root/'test')]).returncode==0
out=HERE/'cpp-dispatch-check-01';out.mkdir(exist_ok=False)
report=dict(passed=True,actual_source_fragment_sha256=hashlib.sha256(fragment.encode()).hexdigest(),candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
    cases=['Director pre-transport exactly once','NK post-transport exactly once','MMAI post-transport exactly once','no interface','observer throws before transport'],
    fixture=True,real_execution_certified=False,native_games=0,optimizer_steps=0)
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
