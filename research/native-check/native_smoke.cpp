#include <array>
#include <iostream>
#include <span>

int main()
{
    constexpr std::array values{1, 2, 3, 4};
    const std::span<const int> view(values);
    int sum = 0;
    for (const auto value : view)
        sum += value;
    std::cout << "C++20 native toolchain OK; sum=" << sum << '\n';
    return sum == 10 ? 0 : 1;
}
