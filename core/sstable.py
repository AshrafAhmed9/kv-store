from __future__ import annotations
import os
import time
from core.bloom_filter import BloomFilter


class SSTable:
    _TOMBSTONE = "__tombstone__"

    def __init__(self, path: str):
        self._path  = path
        self._index = self._build_index(path)
        self._bloom = BloomFilter.for_capacity(max(len(self._index), 1))
        for key in self._index:
            self._bloom.add(key)

    @staticmethod
    def flush(items: list, path: str) -> SSTable:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            for key, entry in items:
                value  = entry["value"] if entry["value"] is not None else SSTable._TOMBSTONE
                expiry = entry["expiry"] or 0.0
                line   = f"{key}\t{value}\t{expiry}\n"
                f.write(line.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return SSTable(path)


    @staticmethod
    def _build_index(path: str) -> dict[str, int]:
        index: dict[str, int] = {}
        with open(path, "rb") as f:
            while True:
                offset = f.tell()
                line   = f.readline()
                if not line:
                    break
                key = line.decode("utf-8").split("\t", 1)[0]
                index[key] = offset
        return index

    def has_key(self, key: str) -> bool:
        """Does this SSTable have a definitive answer for this key?

        Checks bloom filter first (no disk I/O), then the in-memory index.
        A bloom false-positive that isn't in the index correctly returns False.
        """
        if not self._bloom.might_contain(key):
            return False
        return key in self._index

    def get(self, key: str) -> str | None:
        if not self._bloom.might_contain(key):
            return None
        offset = self._index.get(key)
        if offset is None:
            return None
        with open(self._path, "rb") as f:
            f.seek(offset)
            line = f.readline().decode("utf-8").rstrip("\n")
        key_field, value, expiry_str = line.split("\t")
        if value == SSTable._TOMBSTONE:
            return None
        if float(expiry_str) and time.time() > float(expiry_str):
            return None
        return value

    def keys(self) -> list[str]:
        return list(self._index.keys())
