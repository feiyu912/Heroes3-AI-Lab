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
