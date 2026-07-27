"""KVStore: the engine. Ties WAL + MemTable + SSTables + compaction together.

Write path:  WAL (durable) -> MemTable (fast) -> flush to SSTable when full -> compact.
Read path:   MemTable -> immutable MemTable (if a flush is in flight) -> SSTables, newest first.
The first tier with a definitive answer for a key wins — that's what makes deletes
and overwrites correct across tiers.
"""
from __future__ import annotations
import os
import threading
import time
from kvstore.compaction import compact
from kvstore.memtable import MemTable
from kvstore.sstable import SSTable


class KVStore:
    def __init__(self, wal=None, sst_dir: str = "data/sst",
                 memtable_size: int = 1024 * 1024,
                 compaction_trigger: int = 4,
                 bloom_fp_rate: float = 0.01):
        self._lock = threading.RLock()
        self._wal = wal
        self._sst_dir = sst_dir
        self._memtable_size = memtable_size
        self._compaction_trigger = compaction_trigger
        self._bloom_fp_rate = bloom_fp_rate
        self._flush_counter = 0
        self._memtable = MemTable(size_limit=memtable_size)
        self._immutable: MemTable | None = None
        self._sstables: list[SSTable] = self._load_sstables()
        if wal:
            wal.replay(self)

    def set(self, key: str, value: str, ttl: float | None = None,
            expiry: float | None = None) -> None:
        if expiry is None and ttl is not None:
            expiry = time.time() + ttl
        with self._lock:
            if self._wal:
                self._wal.log("SET", key, value, expiry)
            self._memtable.set(key, value, expiry=expiry)
        self._maybe_flush()

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._get(key)

    def delete(self, key: str) -> bool:
        with self._lock:
            existed = self._get(key) is not None
            self._memtable.delete(key)
            if self._wal:
                self._wal.log("DELETE", key)
        self._maybe_flush()
        return existed

    def incr(self, key: str) -> int:
        with self._lock:
            current = self._get(key)
            new_value = int(current) + 1 if current is not None else 1
            self._memtable.set(key, str(new_value))
            if self._wal:
                self._wal.log("SET", key, str(new_value), None)
        self._maybe_flush()
        return new_value

    def scan(self, start: str, end: str) -> list[tuple[str, str]]:
        """All live (key, value) pairs with start <= key <= end, sorted."""
        with self._lock:
            latest = self._latest_values(start, end)
            return [(k, v) for k, v in sorted(latest.items()) if v is not None]

    def keys(self) -> list[str]:
        """Every live key across all tiers, sorted."""
        with self._lock:
            latest = self._latest_values()
            return sorted(k for k, v in latest.items() if v is not None)

    def _latest_values(self, start: str | None = None,
                       end: str | None = None) -> dict[str, str | None]:
        """Each key's newest value, merged across every tier.

        Tiers are walked oldest-first so that a newer write simply overwrites
        an older one in the dict. A None value means the key was deleted or
        has expired.
        """
        latest: dict[str, str | None] = {}
        for sst in self._sstables:                       # oldest on disk first
            latest.update(sst.range_scan(start, end))
        if self._immutable:
            latest.update(self._immutable.entries(start, end))
        latest.update(self._memtable.entries(start, end))  # newest last, so it wins
        return latest

    def _get(self, key: str) -> str | None:
        if self._memtable.has_key(key):
            return self._memtable.get(key)
        if self._immutable and self._immutable.has_key(key):
            return self._immutable.get(key)
        for sst in reversed(self._sstables):
            if sst.has_key(key):
                return sst.get(key)
        return None

    def _load_sstables(self) -> list[SSTable]:
        if not os.path.isdir(self._sst_dir):
            return []
        self._remove_stale_tmp_files()
        files = sorted(f for f in os.listdir(self._sst_dir) if f.endswith(".sst"))
        return [SSTable(os.path.join(self._sst_dir, f), self._bloom_fp_rate) for f in files]

    def _remove_stale_tmp_files(self) -> None:
        """A leftover .tmp file means a flush or compaction crashed mid-write. The
        real data is still safe in the WAL or the untouched source SSTables."""
        for f in os.listdir(self._sst_dir):
            if f.endswith(".tmp"):
                os.remove(os.path.join(self._sst_dir, f))

    def _maybe_flush(self) -> None:
        with self._lock:
            if not self._memtable.should_flush or self._immutable is not None:
                return
            self._immutable = self._memtable
            self._memtable = MemTable(size_limit=self._memtable_size)
            self._flush_counter += 1
            counter = self._flush_counter

        # Flush to disk outside the lock, so reads/writes aren't blocked during I/O.
        sst_path = os.path.join(self._sst_dir, f"{time.time_ns()}_{counter:04d}.sst")
        new_sst = SSTable.flush(self._immutable.items(), sst_path, self._bloom_fp_rate)

        with self._lock:
            self._sstables.append(new_sst)
            self._immutable = None
            if self._wal:
                self._wal.rotate()  # old segment's data is now safely in an SSTable

        self._maybe_compact()

    def _maybe_compact(self) -> None:
        with self._lock:
            if len(self._sstables) < self._compaction_trigger:
                return
            paths = [sst._path for sst in self._sstables]

        output = os.path.join(self._sst_dir, f"{time.time_ns()}_compacted.sst")
        compact(paths, output)
        new_sst = SSTable(output, self._bloom_fp_rate)

        with self._lock:
            self._sstables = [new_sst]
