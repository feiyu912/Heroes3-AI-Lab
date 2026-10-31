#include <iostream>
#include <vector>
#include <ranges>
#include <numeric>
#include <thread>
int main(){std::vector<int> v{1,2,3}; auto r=v|std::views::transform([](int x){return x*2;}); int s=0; for(int x:r)s+=x;std::thread t([]{});t.join();std::cout<<"CXX20:"<<s<<"\n";return s!=12;}
