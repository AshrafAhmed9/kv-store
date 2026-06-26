from __future__ import annotations
import threading
import time


class Metrics:
    def __init__(self):
        self._lock   = threading.Lock()
        self._reads  = 0
        self._writes = 0
        self._deletes = 0
        self._compactions = 0
        self._compaction_seconds = 0.0
        self._corrupt_records = 0
        self._start  = time.time()

    def record_read(self) -> None:
        with self._lock:
            self._reads += 1

    def record_write(self) -> None:
        with self._lock:
            self._writes += 1

    def record_delete(self) -> None:
        with self._lock:
            self._deletes += 1

    def record_compaction(self, duration: float) -> None:
        with self._lock:
            self._compactions += 1
            self._compaction_seconds += duration

    def record_corrupt_record(self) -> None:
        with self._lock:
            self._corrupt_records += 1

    def snapshot(self, key_count: int, memtable_size: int = 0,
                 sstable_count: int = 0, wal_segment_count: int = 0) -> dict:
        with self._lock:
            return {
                "reads":              self._reads,
                "writes":             self._writes,
                "deletes":            self._deletes,
                "key_count":          key_count,
                "memtable_size_bytes": memtable_size,
                "sstable_count":      sstable_count,
                "wal_segment_count":  wal_segment_count,
                "compactions_total":  self._compactions,
                "compaction_seconds": round(self._compaction_seconds, 4),
                "corrupt_records":    self._corrupt_records,
                "uptime_seconds":     round(time.time() - self._start, 2),
            }

    def prometheus(self, key_count: int, memtable_size: int = 0,
                   sstable_count: int = 0, wal_segment_count: int = 0) -> str:
        s = self.snapshot(key_count, memtable_size, sstable_count, wal_segment_count)
        lines = [
            "# HELP kvstore_reads_total Total read operations",
            "# TYPE kvstore_reads_total counter",
            f"kvstore_reads_total {s['reads']}",
            "# HELP kvstore_writes_total Total write operations",
            "# TYPE kvstore_writes_total counter",
            f"kvstore_writes_total {s['writes']}",
            "# HELP kvstore_deletes_total Total delete operations",
            "# TYPE kvstore_deletes_total counter",
            f"kvstore_deletes_total {s['deletes']}",
            "# HELP kvstore_key_count Current number of live keys",
            "# TYPE kvstore_key_count gauge",
            f"kvstore_key_count {s['key_count']}",
            "# HELP kvstore_memtable_size_bytes Current memtable size in bytes",
            "# TYPE kvstore_memtable_size_bytes gauge",
            f"kvstore_memtable_size_bytes {s['memtable_size_bytes']}",
            "# HELP kvstore_sstable_count Current number of SSTable files",
            "# TYPE kvstore_sstable_count gauge",
            f"kvstore_sstable_count {s['sstable_count']}",
            "# HELP kvstore_wal_segment_count Current WAL segment count",
            "# TYPE kvstore_wal_segment_count gauge",
            f"kvstore_wal_segment_count {s['wal_segment_count']}",
            "# HELP kvstore_compactions_total Total compactions performed",
            "# TYPE kvstore_compactions_total counter",
            f"kvstore_compactions_total {s['compactions_total']}",
            "# HELP kvstore_compaction_seconds_total Cumulative compaction time",
            "# TYPE kvstore_compaction_seconds_total counter",
            f"kvstore_compaction_seconds_total {s['compaction_seconds']}",
            "# HELP kvstore_corrupt_records_total Corrupt records detected",
            "# TYPE kvstore_corrupt_records_total counter",
            f"kvstore_corrupt_records_total {s['corrupt_records']}",
            "# HELP kvstore_uptime_seconds Server uptime in seconds",
            "# TYPE kvstore_uptime_seconds gauge",
            f"kvstore_uptime_seconds {s['uptime_seconds']}",
        ]
        return "\n".join(lines) + "\n"
