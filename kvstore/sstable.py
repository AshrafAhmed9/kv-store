"""An immutable, sorted file on disk — one snapshot of keys at flush time.

Format is plain text lines: "key\\tvalue\\texpiry\\n", sorted by key.
A key→byte-offset index is rebuilt in memory on open, so a lookup is one
seek + one readline instead of scanning the whole file.
"""
from __future__ import annotations
import os
import time
from kvstore.bloom_filter import BloomFilter
from kvstore.record import encode_line, decode_line


class SSTable:
    def __init__(self, path: str, bloom_fp_rate: float = 0.01):
        self._path = path
        self._index = self._build_index(path)
        self._bloom = BloomFilter.for_capacity(max(len(self._index), 1), bloom_fp_rate)
        for key in self._index:
            self._bloom.add(key)

    @staticmethod
    def flush(items: list, path: str, bloom_fp_rate: float = 0.01) -> "SSTable":
        """Write sorted (key, entry) pairs to a new file. Crash-safe: write to a
        temp file, fsync it to physical disk, then atomically rename it into place."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            for key, entry in items:
                f.write(encode_line(key, entry["value"], entry["expiry"]).encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        return SSTable(path, bloom_fp_rate)

    @staticmethod
    def _build_index(path: str) -> dict[str, int]:
        index: dict[str, int] = {}
        with open(path, "rb") as f:
            while True:
                offset = f.tell()
                line = f.readline()
                if not line:
                    break
                key = line.decode("utf-8").split("\t", 1)[0]
                index[key] = offset
        return index

    def has_key(self, key: str) -> bool:
        if not self._bloom.might_contain(key):
            return False
        return key in self._index

    def get(self, key: str) -> str | None:
        if not self._bloom.might_contain(key):
            return None
        offset = self._index.get(key)
        if offset is None:
            return None
        return self._value_at(offset)

    def range_scan(self, start: str | None = None,
                   end: str | None = None) -> list[tuple[str, str | None]]:
        """Sorted (key, value) pairs within [start, end].

        A None bound means unbounded. Tombstones and expired entries come
        back as (key, None) so the caller can use them to mask older
        values from other tiers.
        """
        results = []
        for key in sorted(self._index):
            if start is not None and key < start:
                continue
            if end is not None and key > end:
                break
            results.append((key, self._value_at(self._index[key])))
        return results

    def _value_at(self, offset: int) -> str | None:
        """Read the record stored at a byte offset. None means deleted or expired."""
        with open(self._path, "rb") as f:
            f.seek(offset)
            line = f.readline().decode("utf-8")
        _, value, expiry = decode_line(line)
        if value is None or (expiry and time.time() > expiry):
            return None
        return value
