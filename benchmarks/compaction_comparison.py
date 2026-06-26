"""Compare size-tiered vs leveled compaction on identical workloads.

Measures:
  - Write amplification: total bytes written / user data bytes
  - Space amplification: final disk usage / logical data size
  - Final SSTable count: files a read must potentially check

Run: python -m benchmarks.compaction_comparison
"""
from __future__ import annotations
import os
import sys
import shutil
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.memtable import MemTable
from core.sstable import SSTable
from core.compaction import compact
from core.leveled_compaction import LeveledCompactor


N_FLUSHES = 20
KEYS_PER_FLUSH = 100
TRIGGER = 4


def _flush_memtable(keys: list[tuple[str, str]], path: str) -> str:
    mt = MemTable()
    for k, v in keys:
        mt.set(k, v)
    SSTable.flush(mt.items(), path)
    return path


def _workload():
    """Generate a repeatable workload: N_FLUSHES batches of KEYS_PER_FLUSH keys.
    Later flushes overwrite some earlier keys to simulate real update patterns."""
    batches = []
    for flush in range(N_FLUSHES):
        keys = []
        for i in range(KEYS_PER_FLUSH):
            global_id = flush * KEYS_PER_FLUSH + i
            key = f"key_{global_id % (N_FLUSHES * KEYS_PER_FLUSH // 2):06d}"
            val = f"v{flush}_{i}"
            keys.append((key, val))
        batches.append(keys)
    return batches


def bench_size_tiered(work_dir: str) -> dict:
    sst_dir = os.path.join(work_dir, "size_tiered")
    os.makedirs(sst_dir, exist_ok=True)
    batches = _workload()

    user_bytes = 0
    total_written = 0
    live: list[str] = []
    compaction_count = 0

    for i, batch in enumerate(batches):
        path = os.path.join(sst_dir, f"flush_{i:04d}.sst")
        _flush_memtable(batch, path)
        size = os.path.getsize(path)
        user_bytes += size
        total_written += size
        live.append(path)

        if len(live) >= TRIGGER:
            output = os.path.join(sst_dir, f"compacted_{compaction_count:04d}.sst")
            compact(list(live), output)
            out_size = os.path.getsize(output)
            total_written += out_size
            live = [output]
            compaction_count += 1

    final_bytes = sum(os.path.getsize(p) for p in live if os.path.exists(p))

    return {
        "strategy": "Size-tiered",
        "compactions": compaction_count,
        "write_amp": round(total_written / user_bytes, 2),
        "final_files": len(live),
        "final_bytes": final_bytes,
        "space_amp": round(final_bytes / user_bytes, 2),
    }


def bench_leveled(work_dir: str) -> dict:
    sst_dir = os.path.join(work_dir, "leveled")
    os.makedirs(sst_dir, exist_ok=True)
    batches = _workload()

    compactor = LeveledCompactor(sst_dir, l0_threshold=TRIGGER)

    user_bytes = 0
    for i, batch in enumerate(batches):
        path = os.path.join(sst_dir, f"flush_{i:04d}.sst")
        _flush_memtable(batch, path)
        user_bytes += os.path.getsize(path)
        compactor.add_flush(path)

    final_files = compactor.all_sstables()
    final_bytes = sum(os.path.getsize(p) for p in final_files if os.path.exists(p))

    return {
        "strategy": "Leveled",
        "compactions": compactor.compaction_count,
        "write_amp": round((user_bytes + compactor.bytes_written) / user_bytes, 2),
        "final_files": len(final_files),
        "final_bytes": final_bytes,
        "space_amp": round(final_bytes / user_bytes, 2),
        "levels": compactor.level_summary(),
    }


def main():
    work_dir = os.path.join("data", "compaction_bench")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)

    print(f"\n  Compaction Strategy Comparison")
    print(f"  Workload: {N_FLUSHES} flushes x {KEYS_PER_FLUSH} keys, "
          f"50% key overlap across flushes")
    print("  " + "=" * 65)

    st = bench_size_tiered(work_dir)
    lv = bench_leveled(work_dir)

    print(f"\n  {'Metric':<35} {'Size-tiered':>12} {'Leveled':>12}")
    print("  " + "-" * 65)
    print(f"  {'Compactions run':<35} {st['compactions']:>12} {lv['compactions']:>12}")
    print(f"  {'Write amplification':<35} {st['write_amp']:>11}x {lv['write_amp']:>11}x")
    print(f"  {'Final SSTable count':<35} {st['final_files']:>12} {lv['final_files']:>12}")
    print(f"  {'Final disk usage (KB)':<35} {st['final_bytes']//1024:>12} {lv['final_bytes']//1024:>12}")
    print(f"  {'Space amplification':<35} {st['space_amp']:>11}x {lv['space_amp']:>11}x")

    if "levels" in lv:
        levels_str = "  ".join(f"L{k}:{v}" for k, v in sorted(lv["levels"].items()))
        print(f"  {'Level layout':<35} {'—':>12} {levels_str:>12}")

    print("  " + "=" * 65)
    print()
    print("  Size-tiered: merge all when count hits threshold.")
    print("    + Fewer compaction runs, lower write amplification")
    print("    - Higher space amplification (old data lingers until next compaction)")
    print("    - Read cost unbounded (may check many overlapping files)")
    print()
    print("  Leveled: push files down through levels with non-overlapping ranges.")
    print("    + Bounded space amplification (each key exists in ~1 level)")
    print("    + Bounded read cost (at most 1 file per level to check)")
    print("    - Higher write amplification (data rewritten as it moves down levels)")
    print()

    shutil.rmtree(work_dir)


if __name__ == "__main__":
    main()
