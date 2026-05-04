#include <chrono>
#include <iomanip>
#include <iostream>
#include <string>
#include <unordered_map>

using Clock   = std::chrono::high_resolution_clock;
using Seconds = std::chrono::duration<double>;

double ops_per_sec(int n, double secs) {
    return static_cast<double>(n) / secs;
}

int main() {
    const int N = 1'000'000;

    std::unordered_map<std::string, std::string> store;
    store.reserve(N);  // pre-allocate buckets — avoids rehashing during benchmark

    // SET benchmark
    auto t0 = Clock::now();
    for (int i = 0; i < N; ++i)
        store["k" + std::to_string(i)] = "v" + std::to_string(i);
    double write_secs = Seconds(Clock::now() - t0).count();

    // GET benchmark
    t0 = Clock::now();
    for (int i = 0; i < N; ++i) {
        auto it = store.find("k" + std::to_string(i));
        (void)it;  // tell compiler: yes, we meant to not use this
    }
    double read_secs = Seconds(Clock::now() - t0).count();

    std::cout << std::fixed << std::setprecision(0);
    std::cout << "\n  C++ unordered_map Benchmark  (n=1,000,000)\n";
    std::cout << "  ==========================================\n";
    std::cout << "  Writes: " << ops_per_sec(N, write_secs) << " ops/sec\n";
    std::cout << "  Reads:  " << ops_per_sec(N, read_secs)  << " ops/sec\n";
    std::cout << "  ==========================================\n\n";

    return 0;
}
