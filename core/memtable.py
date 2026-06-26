from __future__ import annotations
import time


class MemTable:
    def __init__(self, size_limit: int = 1024 * 1024):
        self._data: dict[str, dict] = {}
        self._size       = 0
        self._size_limit = size_limit

    def set(self, key: str, value: str, expiry: float | None = None) -> None:
        old = self._data.get(key)
        if old and old["value"]:
            self._size -= len(key) + len(old["value"])
        self._data[key] = {"value": value, "expiry": expiry}
        self._size += len(key) + len(value)

    def delete(self, key: str) -> None:
        old = self._data.get(key)
        if old and old["value"]:
            self._size -= len(key) + len(old["value"])
        self._data[key] = {"value": None, "expiry": None}
        self._size += len(key)

    def get(self, key: str) -> str | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry["expiry"] and time.time() > entry["expiry"]:
            return None
        return entry["value"]

    def has_key(self, key: str) -> bool:
        """Does this MemTable have a definitive answer for this key?

        True means stop searching older tiers — even if get() returns None
        (tombstone or expired), this tier is authoritative for this key.
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
