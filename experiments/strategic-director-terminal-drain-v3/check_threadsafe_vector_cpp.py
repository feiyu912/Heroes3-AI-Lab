"""Compile/run the actual extracted candidate class, CPU threads only, not VCMI."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
SUPPORT=r'''
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <exception>
#include <future>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>
struct TerminationRequestedException : std::exception {};
namespace vstd {
template<class C,class T> bool contains(const C &c,const T &t){return std::find(c.begin(),c.end(),t)!=c.end();}
template<class C,class T> auto find(C &c,const T &t){return std::find(c.begin(),c.end(),t);}
}
'''
TEST=r'''
int main(){
 using namespace std::chrono_literals;
 int checks=0;
 {
  ThreadSafeVector<int> q;q.pushBack(3);q.pushBack(5);
  assert((q.snapshot()==std::vector<int>{3,5}));assert(q.tryRemovingElement(3));
  assert(!q.tryRemovingElement(3));assert((q.snapshot()==std::vector<int>{5}));++checks;
 }
 {
  ThreadSafeVector<int> q;q.pushBack(7);std::promise<void> entering;auto ready=entering.get_future();
  auto waiter=std::async(std::launch::async,[&]{entering.set_value();q.waitWhileContains(7);return true;});
  ready.get();assert(waiter.wait_for(20ms)==std::future_status::timeout);
  assert(q.tryRemovingElement(7));assert(waiter.wait_for(1s)==std::future_status::ready);assert(waiter.get());++checks;
 }
 {
  ThreadSafeVector<int> q;q.pushBack(11);q.pushBack(12);std::promise<void> entering;auto ready=entering.get_future();
  auto waiter=std::async(std::launch::async,[&]{entering.set_value();try{q.waitWhileContains(11);}catch(const TerminationRequestedException &){return true;}return false;});
  ready.get();auto removed=q.requestTerminationWithSnapshot();assert((removed==std::vector<int>{11,12}));
  assert(waiter.wait_for(1s)==std::future_status::ready && waiter.get());assert(q.empty());++checks;
  bool threw=false;try{q.pushBack(13);}catch(const TerminationRequestedException &){threw=true;}assert(threw);++checks;
  assert(!q.tryRemovingElement(11));assert(!q.tryRemovingElement(99));++checks;
  bool lateWaitThrew=false;try{q.waitWhileContains(999);}catch(const TerminationRequestedException &){lateWaitThrew=true;}assert(lateWaitThrew);++checks;
  assert(q.requestTerminationWithSnapshot().empty());++checks;
 }
 {
  ThreadSafeVector<int> q;q.pushBack(17);q.requestTermination();
  bool threw=false;try{q.pushBack(18);}catch(const TerminationRequestedException &){threw=true;}assert(threw);
  assert(q.empty() && !q.tryRemovingElement(17));++checks;
 }
 unsigned acceptedTotal=0,rejectedTotal=0;
 for(int round=0;round<30;++round){
  ThreadSafeVector<int> q;std::atomic<bool> start{false};std::mutex resultMutex;
  std::vector<int> accepted;std::atomic<unsigned> rejected{0};std::vector<std::thread> writers;
  for(int t=0;t<8;++t)writers.emplace_back([&,t]{
   while(!start.load(std::memory_order_acquire))std::this_thread::yield();
   for(int i=0;i<32;++i){const int id=t*32+i+1;
    try{q.pushBack(id);std::lock_guard<std::mutex> lock(resultMutex);accepted.push_back(id);}
    catch(const TerminationRequestedException &){++rejected;}
   }
  });
  start.store(true,std::memory_order_release);std::this_thread::yield();
  auto removed=q.requestTerminationWithSnapshot();for(auto &t:writers)t.join();
  std::sort(removed.begin(),removed.end());std::sort(accepted.begin(),accepted.end());
  assert(accepted==removed);assert(accepted.size()+rejected.load()==256);assert(q.empty());
  acceptedTotal+=accepted.size();rejectedTotal+=rejected.load();++checks;
 }
 for(int round=0;round<100;++round){
  ThreadSafeVector<int> q;q.pushBack(501);std::atomic<bool> start{false};bool actualRemove=false;
  std::thread ack([&]{while(!start.load(std::memory_order_acquire))std::this_thread::yield();actualRemove=q.tryRemovingElement(501);});
  start.store(true,std::memory_order_release);auto cancelled=q.requestTerminationWithSnapshot();ack.join();
  assert(q.empty());assert(actualRemove ? cancelled.empty() : cancelled==std::vector<int>{501});++checks;
 }
 std::cout << "{\"passed\":true,\"cpu_class_checks\":" << checks
           << ",\"producer_termination_races\":30,\"ack_termination_races\":100,\"pushes_accepted\":" << acceptedTotal
           << ",\"late_pushes_rejected\":" << rejectedTotal << "}\n";
}
'''


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    header=HERE/'candidate/client/Client.h';original=header.read_text()
    begin=original.index('template<typename T>\nclass ThreadSafeVector')
    end=original.index('\nclass CPlayerEnvironment',begin)
    fragment=original[begin:end]
    fragment_path=args.out/'actual-class-fragment.h';fragment_path.write_text(fragment)
    source=args.out/'threaded-check.cpp';source.write_text(SUPPORT+'\n'+fragment+'\n'+TEST)
    executable=args.out/'threaded-check'
    command=['g++','-std=c++17','-pthread','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(executable)]
    compile_result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    (args.out/'compile.log').write_text(compile_result.stdout+'\nSTDERR:\n'+compile_result.stderr)
    if compile_result.returncode:raise RuntimeError('Actual extracted class failed CPU compilation')
    run=subprocess.run([str(executable)],capture_output=True,text=True,timeout=20)
    (args.out/'run.log').write_text(run.stdout+'\nSTDERR:\n'+run.stderr)
    if run.returncode:raise RuntimeError('Actual extracted class failed threaded CPU checks')
    outcome=json.loads(run.stdout);assert outcome['passed'] and outcome['cpu_class_checks']==138
    result=dict(passed=True,fixture=True,real_execution_certified=False,native_engine_builds=0,native_engine_runs=0,
                cpu_class_compilations=1,cpu_test_executable_runs=1,GPU_operations=0,optimizer_steps=0,training_samples=0,
                checks=outcome,source_sha256={str(path):sha(path) for path in [Path(__file__),header,fragment_path,source,executable]},
                compiler_command=command,
                scope='Exact candidate ThreadSafeVector class extracted unchanged, with standard-library vstd/exception support shims. Real concurrent CPU boundary checks, not an engine compile/game or native proof.')
    (args.out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
