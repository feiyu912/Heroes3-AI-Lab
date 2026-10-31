
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

template<typename T>
class ThreadSafeVector
{
	using TLock = std::unique_lock<std::mutex>;
	std::vector<T> items;
	std::mutex mx;
	std::condition_variable cond;
	std::atomic<bool> isTerminating = false;

public:
	void requestTermination()
	{
		isTerminating = true;
		clear();
	}

	std::vector<T> requestTerminationWithSnapshot()
	{
		TLock lock(mx);
		isTerminating = true;
		const auto terminated = items;
		items.clear();
		cond.notify_all();
		return terminated;
	}

	void clear()
	{
		TLock lock(mx);
		items.clear();
		cond.notify_all();
	}

	void pushBack(const T & item)
	{
		TLock lock(mx);
		if(isTerminating)
			throw TerminationRequestedException();
		items.push_back(item);
		cond.notify_all();
	}

	bool empty()
	{
		TLock lock(mx);
		return items.empty();
	}

	std::vector<T> snapshot()
	{
		TLock lock(mx);
		return items;
	}

	void waitWhileContains(const T & item)
	{
		TLock lock(mx);
		cond.wait(lock, [this, &item](){ return isTerminating || !vstd::contains(items, item);});

		if (isTerminating)
			throw TerminationRequestedException();
	}

	bool tryRemovingElement(const T & item) //returns false if element was not present
	{
		TLock lock(mx);
		if(isTerminating)
			return false;
		auto itr = vstd::find(items, item);
		if(itr == items.end()) //not in container
		{
			return false;
		}

		items.erase(itr);
		cond.notify_all();
		return true;
	}
};


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
