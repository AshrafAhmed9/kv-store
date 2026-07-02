from __future__ import annotations
import time
import config
from core.store import KVStore


class RateLimiter:
    def __init__(self, store: KVStore, limit: int | None = None, window: int | None = None):
        conf = config.load()
        self._store  = store
        self._limit  = limit if limit is not None else conf.rate_limit
        self._window = window if window is not None else conf.rate_window

    def _key(self, user_id: str) -> str:
        window_id = int(time.time() // self._window)
        return f"rate:{user_id}:{window_id}"

    def is_allowed(self, user_id: str) -> bool:
        key = self._key(user_id)
        raw = self._store.get(key)
        if raw is None:
            self._store.set(key, "1", ttl=self._window)
            return True
        if int(raw) >= self._limit:
            return False
        self._store.incr(key)
        return True

    def remaining(self, user_id: str) -> int:
        raw = self._store.get(self._key(user_id))
        return max(0, self._limit - int(raw)) if raw else self._limit
