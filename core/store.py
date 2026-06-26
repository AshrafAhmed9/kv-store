from __future__ import annotations
import os
import threading
import time
from core.compaction import compact
from core.memtable import MemTable
from core.sstable import SSTable


class KVStore:
    def __init__(self, wal=None, sst_dir: str = "data/sst",
                 memtable_size: int = 1024 * 1024,
                 compaction_trigger: int = 4):
        self._lock = threading.RLock()
        self._wal = wal
        self._sst_dir = sst_dir
        self._memtable_size = memtable_size
        self._compaction_trigger = compaction_trigger
        self._flush_counter = 0
        self._memtable = MemTable(size_limit=memtable_size)
        self._immutable: MemTable | None = None
        self._sstables: list[SSTable] = self._load_sstables()
        if wal:
            wal.replay(self)

    def _load_sstables(self) -> list[SSTable]:
        if not os.path.isdir(self._sst_dir):
            return []
        for f in os.listdir(self._sst_dir):
            if f.endswith(".tmp"):
                os.remove(os.path.join(self._sst_dir, f))
        files = sorted(f for f in os.listdir(self._sst_dir) if f.endswith(".sst"))
        return [SSTable(os.path.join(self._sst_dir, f)) for f in files]

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

    def _get(self, key: str) -> str | None:
        if self._memtable.has_key(key):
            return self._memtable.get(key)

        if self._immutable and self._immutable.has_key(key):
            return self._immutable.get(key)

        for sst in reversed(self._sstables):
            if sst.has_key(key):
                return sst.get(key)

        return None

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
            val = int(current) + 1 if current is not None else 1
            self._memtable.set(key, str(val))
            if self._wal:
                self._wal.log("SET", key, str(val), None)
        self._maybe_flush()
        return val

    def scan(self, start: str, end: str) -> list[tuple[str, str]]:
        with self._lock:
            merged: dict[str, str | None] = {}

            for sst in self._sstables:
                for key, value in sst.range_scan(start, end):
                    merged[key] = value

            if self._immutable:
                for key in sorted(self._immutable._data):
                    if key < start or key > end:
                        continue
                    merged[key] = self._immutable.get(key)

            for key in sorted(self._memtable._data):
                if key < start or key > end:
                    continue
                merged[key] = self._memtable.get(key)

            return [(k, v) for k, v in sorted(merged.items()) if v is not None]

    def keys(self) -> list[str]:
        with self._lock:
            seen: set[str] = set()
            live: list[str] = []

            for key in self._memtable._data:
                seen.add(key)
                if self._memtable.get(key) is not None:
                    live.append(key)

            if self._immutable:
                for key in self._immutable._data:
                    if key not in seen:
                        seen.add(key)
                        if self._immutable.get(key) is not None:
                            live.append(key)

            for sst in reversed(self._sstables):
                for key in sst.keys():
                    if key not in seen:
                        seen.add(key)
                        if sst.get(key) is not None:
                            live.append(key)

            return live

    def _maybe_flush(self) -> None:
        with self._lock:
            if not self._memtable.should_flush:
                return
            if self._immutable is not None:
                return
            self._immutable = self._memtable
            self._memtable = MemTable(size_limit=self._memtable_size)
            self._flush_counter += 1
            counter = self._flush_counter

        sst_path = os.path.join(self._sst_dir, f"{time.time_ns()}_{counter:04d}.sst")
        new_sst = SSTable.flush(self._immutable.items(), sst_path)

        with self._lock:
            self._sstables.append(new_sst)
            self._immutable = None
            if self._wal:
                self._wal.rotate()

        self._maybe_compact()

    def _maybe_compact(self) -> None:
        with self._lock:
            if len(self._sstables) < self._compaction_trigger:
                return
            paths = [sst._path for sst in self._sstables]

        output = os.path.join(self._sst_dir, f"{time.time_ns()}_compacted.sst")
        compact(paths, output)
        new_sst = SSTable(output)

        with self._lock:
            self._sstables = [new_sst]
