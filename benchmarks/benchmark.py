from __future__ import annotations
import os
import time
import tracemalloc
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.store import KVStore
from core.wal import WAL


def bench_writes(n: int = 100_000) -> float:
    store = KVStore()
    start = time.perf_counter()
    for i in range(n):
        store.set(f"k{i}", f"v{i}")
    return n / (time.perf_counter() - start)


def bench_reads(n: int = 100_000) -> tuple[float, float]:
    store = KVStore()
    for i in range(n):
        store.set(f"k{i}", f"v{i}")
    start = time.perf_counter()
    for i in range(n):
        store.get(f"k{i}")
    elapsed = time.perf_counter() - start
    return n / elapsed, (elapsed / n) * 1000


def bench_wal_writes(n: int = 100_000) -> float:
    wal_path = os.path.join("data", "bench.log")
    wal   = WAL(wal_path, sync_every=100)
    store = KVStore(wal=wal)
    start = time.perf_counter()
    for i in range(n):
        store.set(f"k{i}", f"v{i}")
    ops = n / (time.perf_counter() - start)
    wal.close()
    try:
        os.remove(wal_path)
    except FileNotFoundError:
        pass
    return ops


def bench_memory(n: int = 10_000) -> float:
    store = KVStore()
    tracemalloc.start()
    for i in range(n):
        store.set(f"k{i}", f"v{i}")
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak / 1024


def _row(label: str, result: str, target: str, passed: bool) -> None:
    status = "PASS" if passed else "FAIL"
    print(f"  {label:<38} {result:>12}  {target:>10}  {status}")


def main() -> None:
    print("\n  KV Store Benchmark Results")
    print("  " + "=" * 68)
    print(f"  {'Metric':<38} {'Result':>12}  {'Target':>10}  Status")
    print("  " + "-" * 68)

    write_ops            = bench_writes()
    read_ops, avg_lat_ms = bench_reads()
    wal_ops              = bench_wal_writes()
    peak_kb              = bench_memory()

    _row("Write throughput, no WAL (ops/sec)", f"{write_ops:>12,.0f}", ">=100,000", write_ops >= 100_000)
    _row("Write throughput, WAL (ops/sec)",    f"{wal_ops:>12,.0f}",   ">=100,000", wal_ops   >= 100_000)
    _row("Read throughput (ops/sec)",          f"{read_ops:>12,.0f}",  ">=100,000", read_ops  >= 100_000)
    _row("Avg read latency (ms)",              f"{avg_lat_ms:>12.4f}", "<1ms",      avg_lat_ms < 1.0)
    _row("Peak memory, 10k keys (KB)",         f"{peak_kb:>12,.1f}",   "-",         True)

    print("  " + "=" * 68)
    print("  WAL uses sync_every=100 (batch mode). Default is sync_every=1.\n")


if __name__ == "__main__":
    main()
