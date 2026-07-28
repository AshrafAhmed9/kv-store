"""The on-disk line format shared by SSTables and compaction output.

One format, defined once, so a file written by a flush is guaranteed
readable by compaction and vice versa — they can never silently drift apart.
"""
from __future__ import annotations

TOMBSTONE = "__tombstone__"


def encode_line(key: str, value: str | None, expiry: float | None) -> str:
    stored_value = value if value is not None else TOMBSTONE
    return f"{key}\t{stored_value}\t{expiry or 0.0}\n"


def decode_line(line: str) -> tuple[str, str | None, float]:
    """Split a stored line back into (key, value, expiry). value is None for a tombstone."""
    key, stored_value, expiry_str = line.rstrip("\n").split("\t")
    value = None if stored_value == TOMBSTONE else stored_value
    return key, value, float(expiry_str)
