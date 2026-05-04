from __future__ import annotations
import json
import config
from core.store import KVStore


class SessionStore:
    def __init__(self, store: KVStore):
        self._store = store

    def create(self, user_id: str, data: dict, ttl: float = 1800) -> None:
        self._store.set(f"sess:{user_id}", json.dumps(data), ttl=ttl)

    def get(self, user_id: str) -> dict | None:
        raw = self._store.get(f"sess:{user_id}")
        return json.loads(raw) if raw is not None else None

    def invalidate(self, user_id: str) -> bool:
        return self._store.delete(f"sess:{user_id}")
