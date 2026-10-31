"""Compile actual trace function with synthetic snapshot/logger stubs, not native evidence."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent

def main():
    source=(HERE/'SupplyAdapter.inc').read_text()
    start=source.index('void CDirectorAI::supplyTrace(')
    end=source.index('void CDirectorAI::supplyQueueReply(',start)
    extracted=source[start:end]
    stub=r'''
#include "SupplyController.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <cstdlib>
struct ID {int getNum() const {return 0;}};
struct Calendar {int getCurrentDay() const {return 42;}};
struct Callback {Calendar getCalendar() const {return {};}};
struct Logger {std::vector<std::string> lines;void info(const char*,const std::string&json){lines.push_back(json);}};
Logger logger;Logger*logGlobal=&logger;
class CDirectorAI
{
public:
 ID playerID;Callback callback;Callback*cb=&callback;
 supply_v1::Controller supply;supply_v1::World world;
 supply_v1::World supplyWorld() const {return world;}
 void supplyTrace(const std::string&event,int id=-1,const std::string&actualRequest="") const;
};
'''
    tail=r'''
int main(int argc,char**argv)
{
 if(argc!=2)return 2;
 setenv("LAB_ADV_SUPPLY_TRACE",argv[1],1);
 CDirectorAI ai;ai.supply.main=8;ai.supply.courier=19;ai.supply.home=3;
 supply_v1::Hero m;m.id=8;m.movement=1200;m.pos={8,4,0};m.army[0]={0,5};
 supply_v1::Hero c;c.id=19;c.movement=900;c.pos={2,4,0};c.army[1]={2,3};
 ai.world.heroes={m,c};supply_v1::Town t;t.id=3;t.visitor=19;t.pos={2,4,0};t.army[0]={0,10};ai.world.towns={t};
 ai.supply=supply_v1::Controller{};ai.supply.start(ai.world);ai.supply.beginTurn(ai.world);ai.supply.cursor=1;
 ai.supplyTrace("synthetic_initial",-1);
 auto cmd=ai.supply.next(ai.world,supply_v1::Pos{9,4,0});if(!cmd)return 4;
 ai.supply.prepare(*cmd);ai.supply.bind(17,supply_v1::Op::Transfer);
 ai.world.towns[0].army[0]=supply_v1::Stack{};ai.world.heroes[1].army[0]={0,10};
 ai.supplyTrace("synthetic_after_state_delta",17,"{\"request_id\":17,\"op\":\"ArrangeStacks\"}");
 ai.supply.ack(17,supply_v1::Op::Transfer,true,ai.world);ai.supplyTrace("synthetic_control_ack_applied",17);
 for(const auto&line:logger.lines)std::cout<<line<<'\n';
 unsetenv("LAB_ADV_SUPPLY_TRACE");
 ai.supplyTrace("synthetic_without_file",18);
 return logger.lines.size()==4?0:3;
}
'''
    with tempfile.TemporaryDirectory(prefix='supply-trace-cpu-') as temp:
        temp=Path(temp);cpp=temp/'trace.cpp';cpp.write_text(stub+extracted+tail)
        binary=temp/'trace';target=temp/'trace.jsonl'
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-pedantic','-I',str(HERE),str(cpp),'-o',str(binary)],check=True)
        proc=subprocess.run([str(binary),str(target)],check=True,capture_output=True,text=True)
        assert proc.stdout==target.read_text(), 'mirror and file differ'
        rows=[json.loads(line) for line in proc.stdout.splitlines()]
        assert len(rows)==3
        before,after,control=rows
        assert before['towns'][0]=={'id':3,'visitor':19,'position':[2,4,0],
                                   'army':[[0,10]]+[[-1,0]]*6}
        assert len(before['roster'])==2 and all(len(h['army'])==7 for h in before['roster'])
        assert before['towns'][0]['army'][0]==[0,10] and after['towns'][0]['army'][0]==[-1,0]
        assert before['roster'][1]['army'][0]==[-1,0] and after['roster'][1]['army'][0]==[0,10]
        assert after['native_request_id']==17 and after['pending']['actor']==19
        assert after['actual_request']=={'request_id':17,'op':'ArrangeStacks'} and before['actual_request'] is None
        assert all(r['policy_transition'] is False for r in rows)
        assert all(r['schema']=='scripted-supply-events-v3' and r['controller_epoch']=='scripted-supply-cargo-v3' for r in rows)
        assert before['job']['picked']==[] and after['job']['picked']==[] and after['job']['cargo_remaining']==[]
        assert control['job']['picked']==[[0,10]] and control['job']['cargo_remaining']==[[0,10]] and control['job']['cargo_slots'][0]==[0,10]
        assert control['job']['reserve']==[[2,3]] and control['job']['initial_reserve_slots'][1]==[2,3] and control['pending'] is None
    report={'passed':True,'checks':13,'native_games':0,'native_built':False,
            'scope':'actual extracted trace function, synthetic logger/world stubs only',
            'extracted_function_sha256':hashlib.sha256(extracted.encode()).hexdigest(),
            'adapter_sha256':hashlib.sha256(source.encode()).hexdigest()}
    (HERE/'TRACE_CPU_REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
