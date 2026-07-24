"""An immutable, sorted file on disk — one snapshot of keys at flush time.

Format is plain text lines: "key\\tvalue\\texpiry\\n", sorted by key.
A key→byte-offset index is rebuilt in memory on open, so a lookup is one
seek + one readline instead of scanning the whole file.
"""
from __future__ import annotations
import os
import time
from kvstore.bloom_filter import BloomFilter

_TOMBSTONE = "__tombstone__"


class SSTable:
    def __init__(self, path: str):
        self._path = path
        self._index = self._build_index(path)
        self._bloom = BloomFilter.for_capacity(max(len(self._index), 1))
        for key in self._index:
            self._bloom.add(key)

    @staticmethod
    def flush(items: list, path: str) -> "SSTable":
        """Write sorted (key, entry) pairs to a new file. Crash-safe: write to a
        temp file, fsync it to physical disk, then atomically rename it into place."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            for key, entry in items:
                f.write(_encode_line(key, entry["value"], entry["expiry"]))
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
        _, value = _decode_line(self._read_line_at(offset))
        return value

    def range_scan(self, start: str, end: str) -> list[tuple[str, str | None]]:
        """Sorted (key, value) pairs for start <= key <= end.

        Tombstones/expired entries come back as (key, None) so the caller
        can use them to mask older values from other tiers.
        """
        results = []
        for key in sorted(self._index):
            if key < start:
                continue
            if key > end:
                break
            _, value = _decode_line(self._read_line_at(self._index[key]))
            results.append((key, value))
        return results

    def keys(self) -> list[str]:
        return list(self._index.keys())

    def _read_line_at(self, offset: int) -> str:
        with open(self._path, "rb") as f:
            f.seek(offset)
            return f.readline().decode("utf-8").rstrip("\n")


def _encode_line(key: str, value: str | None, expiry: float | None) -> bytes:
    stored_value = value if value is not None else _TOMBSTONE
    line = f"{key}\t{stored_value}\t{expiry or 0.0}\n"
    return line.encode("utf-8")


def _decode_line(line: str) -> tuple[str, str | None]:
    key, value, expiry_str = line.split("\t")
    if value == _TOMBSTONE:
        return key, None
    if float(expiry_str) and time.time() > float(expiry_str):
        return key, None
    return key, value
