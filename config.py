# config.py
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    data_dir: str
    memtable_size: int          # bytes; flush when exceeded
    sync_every: int             # WAL: fsync every N writes (1 = max durability)
    compaction_trigger: int     # compact when SSTable count exceeds this
    bloom_fp_rate: float        # target false-positive rate
    rate_limit: int
    rate_window: int
    server_host: str
    server_port: int
    metrics_port: int

    @property
    def wal_path(self) -> str:
        return os.path.join(self.data_dir, "wal")

    @property
    def sst_dir(self) -> str:
        return os.path.join(self.data_dir, "sst")

    def __post_init__(self) -> None:
        if self.memtable_size <= 0:
            raise ValueError("memtable_size must be > 0")
        if self.sync_every <= 0:
            raise ValueError("sync_every must be >= 1")
        if not (0.0 < self.bloom_fp_rate < 1.0):
            raise ValueError("bloom_fp_rate must be in (0, 1)")
        if self.compaction_trigger <= 0:
            raise ValueError("compaction_trigger must be > 0")


def load() -> Config:
    """Build Config from environment, with sane defaults. Call once at boot."""
    return Config(
        data_dir          = os.environ.get("KV_DATA_DIR", "data"),
        memtable_size     = int(os.environ.get("KV_MEMTABLE_SIZE", 1 * 1024 * 1024)),
        sync_every        = int(os.environ.get("KV_SYNC_EVERY", "1")),
        compaction_trigger= int(os.environ.get("KV_COMPACTION_TRIGGER", "4")),
        bloom_fp_rate     = float(os.environ.get("KV_BLOOM_FP_RATE", "0.01")),
        rate_limit        = int(os.environ.get("KV_RATE_LIMIT", "10")),
        rate_window       = int(os.environ.get("KV_RATE_WINDOW", "60")),
        server_host       = os.environ.get("KV_HOST", "127.0.0.1"),
        server_port       = int(os.environ.get("KV_PORT", "6379")),
        metrics_port      = int(os.environ.get("KV_METRICS_PORT", "6380")),
    )
