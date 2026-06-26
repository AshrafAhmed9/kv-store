# core/durability.py
from __future__ import annotations
import os


def atomic_write(path: str, data: bytes) -> None:
    """Write `data` to `path` so a crash never leaves a partial file.

    tmp file -> flush -> fsync -> atomic os.replace.
    A crash before replace leaves the old file intact; after, the new one.
    """
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())          # the step that actually hits the disk
    os.replace(tmp, path)             # atomic on the same filesystem


def fsync_dir(path: str) -> None:
    """Fsync a directory so the rename itself is durable (POSIX only).

    On Windows you cannot open a directory as a file descriptor, so this
    is a no-op there — os.replace is already durable on NTFS.
    """
    if os.name != "posix":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
