"""The in-memory write buffer that every write lands in first.

Reads check here before touching disk, so recently-written keys are O(1).
A delete does not remove the key — it stores a "tombstone" (value=None) so
that an older value sitting in an SSTable on disk doesn't reappear.
"""
from __future__ import annotations
import time


class MemTable:
    def __init__(self, size_limit: int = 1024 * 1024):
        self._data: dict[str, dict] = {}
        self._size = 0
        self._size_limit = size_limit

    def set(self, key: str, value: str, expiry: float | None = None) -> None:
        self._forget_old_size(key)
        self._data[key] = {"value": value, "expiry": expiry}
        self._size += len(key) + len(value)

    def delete(self, key: str) -> None:
        self._forget_old_size(key)
        self._data[key] = {"value": None, "expiry": None}
        self._size += len(key)

    def _forget_old_size(self, key: str) -> None:
        old = self._data.get(key)
        if old and old["value"]:
            self._size -= len(key) + len(old["value"])

    def get(self, key: str) -> str | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry["expiry"] and time.time() > entry["expiry"]:
            return None
        return entry["value"]

    def has_key(self, key: str) -> bool:
        """True if this MemTable has a definitive answer for this key.

        A caller should stop searching older tiers whenever this is True,
        even if get() itself returns None (a tombstone or an expired value).
        """
        return key in self._data

    @property
    def should_flush(self) -> bool:
        return self._size >= self._size_limit

    def items(self) -> list:
        return sorted(self._data.items())

    def clear(self) -> None:
        self._data.clear()
        self._size = 0
