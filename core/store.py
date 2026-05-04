from __future__ import annotations
import threading
import time
# ... rest unchanged

import threading
import time


class KVStore:
    def __init__(self, wal=None):
        self._data: dict[str, dict] = {}
        self._lock = threading.RLock()
        self._wal = wal
        if wal:
            wal.replay(self)

    def set(self, key: str, value: str, ttl: float | None = None, expiry: float | None = None) -> None:
        if expiry is None and ttl is not None:
            expiry = time.time() + ttl
        with self._lock:
            self._data[key] = {"value": value, "expires_at": expiry}
            if self._wal:
                self._wal.log("SET", key, value, expiry)

    def get(self, key: str) -> str | None:
        with self._lock:
            if key not in self._data:
                return None
            if self._is_expired(key):
                del self._data[key]
                return None
            return self._data[key]["value"]

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._data:
                del self._data[key]
                if self._wal:
                    self._wal.log("DELETE", key)
                return True
            return False

    def incr(self, key: str) -> int:
        with self._lock:
            current = self._data.get(key)
            is_alive = current is not None and not self._is_expired(key)
            val = int(current["value"]) + 1 if is_alive else 1
            expiry = current["expires_at"] if is_alive else None
            self._data[key] = {"value": str(val), "expires_at": expiry}
            if self._wal:
                self._wal.log("SET", key, str(val), expiry)
            return val

    def _is_expired(self, key: str) -> bool:
        entry = self._data.get(key)
        if entry is None:
            return False
        expires_at = entry["expires_at"]
        return expires_at is not None and time.time() > expires_at

    def keys(self) -> list[str]:
        with self._lock:
            return [k for k in self._data if not self._is_expired(k)]
