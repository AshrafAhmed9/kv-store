import os

DATA_DIR      = "data"
WAL_PATH      = os.path.join(DATA_DIR, "wal.log")
SST_DIR       = os.path.join(DATA_DIR, "sst")
MEMTABLE_SIZE = 1 * 1024 * 1024
DEFAULT_TTL   = None
RATE_LIMIT    = 10
RATE_WINDOW   = 60
SERVER_HOST   = "127.0.0.1"
SERVER_PORT   = 6379
