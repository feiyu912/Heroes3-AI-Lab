"""Compile actual header predicates and wire parsing; CPU only, no engine execution."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;header=HERE/'candidate/AI/DirectorAI/TypedPolicyProtocol.h'
source=r'''
#include "HEADER"
#include <cassert>
#include <climits>
int main(){
 using namespace LabThreatReplan;
 assert(pressure(0,0,0,100,12,-12,0,150));
 assert(!pressure(0,0,0,100,13,0,0,150));
 assert(!pressure(0,0,0,100,0,0,1,150));
 assert(!pressure(0,0,0,100,1,1,0,149.999));
 assert(!pressure(0,0,0,0,1,1,0,150));
 assert(!pressure(0,0,0,-1,1,1,0,150));
 assert(!pressure(0,0,0,100,1,1,0,std::numeric_limits<double>::quiet_NaN()));
 assert(!pressure(0,0,0,std::numeric_limits<double>::infinity(),1,1,0,150));
 assert(!pressure(INT_MIN,INT_MAX,0,100,INT_MAX,INT_MIN,0,150));
 assert(allowed(true,true,true,false,2));
 assert(!allowed(false,true,true,false,2));
 assert(!allowed(true,false,true,false,2));
 assert(!allowed(true,true,false,false,2));
 assert(!allowed(true,true,true,true,2));
 assert(!allowed(true,true,true,false,1));
 int released=0;bool used=false;
 for(int i=0;i<128;++i)if(allowed(true,true,true,used,20)){used=true;++released;}
 assert(released==1);used=false;assert(allowed(true,true,true,used,20));
 assert(LabTypedPolicy::sha256("abc")=="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
}
'''.replace('HEADER',str(header))
with tempfile.TemporaryDirectory(prefix='threat-replan-cpp-') as tmp:
    root=Path(tmp);cpp=root/'test.cpp';cpp.write_text(source)
    result=subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-O2',str(cpp),'-o',str(root/'test')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert subprocess.run([str(root/'test')]).returncode==0
out=HERE/'cpp-check-01';out.mkdir(exist_ok=False)
report=dict(passed=True,actual_cpp_compiled=True,assertions=18,header_sha256=hashlib.sha256(header.read_bytes()).hexdigest(),
    native_games=0,optimizer_steps=0,scope='Threshold boundaries, invalid strength/level, overflow-safe coordinate deltas, one-budget predicate and original SHA helper. Not actual native integration proof.')
(out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
