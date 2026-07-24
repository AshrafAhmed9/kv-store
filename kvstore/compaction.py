"""Merge several SSTables into one, dropping dead data.

Called automatically once too many SSTables pile up. Without this, reads
would get slower forever as more files need checking, and disk space would
grow unbounded with old, overwritten, or deleted values.
"""
from __future__ import annotations
import os
import time

_TOMBSTONE = "__tombstone__"


def compact(sst_paths: list[str], output_path: str) -> str:
    merged = _merge_newest_wins(sst_paths)
    _write_atomically(merged, output_path)
    _delete_sources(sst_paths)
    return output_path


def _merge_newest_wins(sst_paths: list[str]) -> dict[str, tuple[str, float]]:
    """Later paths in the list win on key collision, since sst_paths is oldest-first."""
    merged: dict[str, tuple[str, float]] = {}
    for path in sst_paths:
        with open(path, "rb") as f:
            for line in f:
                key, value, expiry_str = line.decode("utf-8").rstrip("\n").split("\t")
                merged[key] = (value, float(expiry_str))
    return merged


def _write_atomically(merged: dict[str, tuple[str, float]], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    now = time.time()
    tmp = output_path + ".tmp"

    with open(tmp, "wb") as out:
        for key in sorted(merged):
            value, expiry = merged[key]
            if value == _TOMBSTONE or (expiry and now > expiry):
                continue
            out.write(f"{key}\t{value}\t{expiry}\n".encode("utf-8"))
        out.flush()
        os.fsync(out.fileno())

    os.replace(tmp, output_path)  # atomic: readers see the old or the new file, never a partial one


def _delete_sources(sst_paths: list[str]) -> None:
    for path in sst_paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
