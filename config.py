import os

DATA_DIR      = os.environ.get("KV_DATA_DIR", "data")
WAL_PATH      = os.path.join(DATA_DIR, "wal.log")
SST_DIR       = os.path.join(DATA_DIR, "sst")
MEMTABLE_SIZE = 1 * 1024 * 1024
DEFAULT_TTL   = None
RATE_LIMIT    = int(os.environ.get("KV_RATE_LIMIT", "10"))
RATE_WINDOW   = int(os.environ.get("KV_RATE_WINDOW", "60"))
SERVER_HOST   = os.environ.get("KV_HOST", "127.0.0.1")
SERVER_PORT   = int(os.environ.get("KV_PORT", "6379"))
METRICS_PORT  = int(os.environ.get("KV_METRICS_PORT", "6380"))
