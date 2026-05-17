from __future__ import annotations
import threading
import time


class Metrics:
    def __init__(self):
        self._lock   = threading.Lock()
        self._reads  = 0
        self._writes = 0
        self._start  = time.time()

    def record_read(self) -> None:
        with self._lock:
            self._reads += 1

    def record_write(self) -> None:
        with self._lock:
            self._writes += 1

    def snapshot(self, key_count: int) -> dict:
        with self._lock:
            return {
                "reads":          self._reads,
                "writes":         self._writes,
                "key_count":      key_count,
                "uptime_seconds": round(time.time() - self._start, 2),
            }
