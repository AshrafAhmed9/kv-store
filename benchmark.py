"""Measures real write/read throughput. Run: python benchmark.py

Every number printed here is measured on this machine, right now — nothing
is hardcoded. Re-run it before quoting a number anywhere.
"""
from __future__ import annotations
import os
import shutil
import time
from kvstore.store import KVStore
from kvstore.wal import WAL

_BENCH_DIR = "data/_benchmark_scratch"


def bench_writes_no_wal(n: int = 100_000) -> float:
    store = KVStore(sst_dir=f"{_BENCH_DIR}/sst")
    start = time.perf_counter()
    for i in range(n):
        store.set(f"k{i}", f"v{i}")
    return n / (time.perf_counter() - start)


def bench_writes_with_wal(n: int, sync_every: int) -> float:
    wal_dir = f"{_BENCH_DIR}/wal_{sync_every}"
    wal = WAL(wal_dir, sync_every=sync_every)
    store = KVStore(wal=wal, sst_dir=f"{_BENCH_DIR}/sst_wal_{sync_every}")
    start = time.perf_counter()
    for i in range(n):
        store.set(f"k{i}", f"v{i}")
    ops = n / (time.perf_counter() - start)
    wal.close()
    return ops


def bench_reads(n: int = 100_000) -> tuple[float, float]:
    store = KVStore(sst_dir=f"{_BENCH_DIR}/sst_read")
    for i in range(n):
        store.set(f"k{i}", f"v{i}")
    start = time.perf_counter()
    for i in range(n):
        store.get(f"k{i}")
    elapsed = time.perf_counter() - start
    return n / elapsed, (elapsed / n) * 1000


def _print_row(label: str, ops: float) -> None:
    print(f"  {label:<42} {ops:>12,.0f} ops/sec")


def main() -> None:
    if os.path.exists(_BENCH_DIR):
        shutil.rmtree(_BENCH_DIR)

    print("\n  KV Store Benchmark (measured now, not hardcoded)")
    print("  " + "=" * 60)

    _print_row("Write, no WAL", bench_writes_no_wal())
    _print_row("Write, WAL batched (sync_every=100)", bench_writes_with_wal(100_000, 100))
    _print_row("Write, WAL fsync-per-write (sync_every=1)", bench_writes_with_wal(10_000, 1))
    read_ops, avg_ms = bench_reads()
    _print_row("Read", read_ops)
    print(f"  {'Avg read latency':<42} {avg_ms:>12.4f} ms")

    print("  " + "=" * 60 + "\n")
    shutil.rmtree(_BENCH_DIR)


if __name__ == "__main__":
    main()
