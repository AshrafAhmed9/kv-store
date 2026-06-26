# core/errors.py
from __future__ import annotations


class KVStoreError(Exception):
    """Base class for all storage-engine errors."""


class CorruptRecordError(KVStoreError):
    """A WAL or SSTable record failed its CRC / format check."""


class WALError(KVStoreError):
    """Write-ahead-log read/write/rotation failure."""


class CompactionError(KVStoreError):
    """SSTable merge/compaction failure."""
