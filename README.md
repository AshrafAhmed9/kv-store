# KV Store

A high-performance key-value store built from scratch in Python, modeled after Redis internals.
Used as a caching and rate-limiting layer for backend services.

> "I built a custom key-value store and used it as a session cache and rate-limiting backend,
> similar to how Redis is used in production systems."

## Architecture

```
Client (TCP)
    │
    ▼
Server (ThreadingTCPServer — one thread per client)
    │
    ▼
KVStore (thread-safe in-memory hashmap + lazy TTL eviction)
    │
    ├── WAL (Write-Ahead Log — crash recovery, idempotent replay)
    │
    └── SSTable (immutable sorted files + in-memory key→offset index)

Features/
    ├── SessionStore  (TTL-based sessions backed by KVStore)
    └── RateLimiter   (fixed-window counter, O(1) time and space)
```

## Features

| Feature | Detail |
|---|---|
| GET / SET / DELETE / INCR | Core operations, O(1) average |
| TTL (key expiry) | Lazy eviction — checked on access, no background scanner |
| Write-Ahead Log | Crash recovery with idempotent replay via op IDs |
| TCP server | Multi-client, one thread per connection |
| Line protocol | Redis-inspired: `+OK`, `$value`, `:integer`, `-ERR` |
| Session store | JSON-encoded sessions with TTL auto-expiry |
| Rate limiter | Fixed-window counter — O(1), auto-resets each window |
| SSTable | Immutable sorted disk files with in-memory byte-offset index |
| Benchmarks | Measured throughput, latency, and WAL overhead |

## Performance

Benchmarked on a standard laptop (Python 3.8, Windows 11):

| Metric | Result |
|---|---|
| Write throughput (no WAL) | 938,803 ops/sec |
| Write throughput (WAL, batch sync) | 150,180 ops/sec |
| Read throughput | 1,161,549 ops/sec |
| Avg read latency | 0.0009 ms |
| C++ unordered_map writes | 2,657,691 ops/sec |
| C++ unordered_map reads | 28,862,028 ops/sec |

C++ reads are ~25x faster than Python due to zero interpreter overhead and no object boxing.
Python WAL throughput uses `sync_every=100` (batch mode). Default is `sync_every=1` for maximum durability.

## Running

**Start the server:**
```bash
python -m server.server
```

**Connect a client (separate terminal):**
```bash
python -m server.client
```

**Commands:**
```
SET name Alice
GET name
SET session abc EX 30
INCR counter
KEYS
DELETE name
quit
```

**Run benchmarks:**
```bash
python -m benchmarks.benchmark
```

**Run C++ benchmark:**
```bash
g++ -O2 -std=c++17 -o cpp/benchmark cpp/benchmark.cpp
cpp/benchmark.exe
```

## Project Structure

```
kv_store/
├── config.py               # Central config (ports, paths, thresholds)
├── core/
│   ├── store.py            # In-memory KVStore — hashmap + TTL + thread-safety
│   ├── wal.py              # Write-Ahead Log — durability + idempotent replay
│   ├── memtable.py         # LSM memtable — in-memory write buffer
│   └── sstable.py          # SSTable — immutable sorted disk files + O(1) index
├── server/
│   ├── protocol.py         # Line protocol parser
│   ├── server.py           # TCP server (ThreadingTCPServer)
│   └── client.py           # CLI client
├── features/
│   ├── session_store.py    # Session management with TTL
│   └── rate_limiter.py     # Fixed-window rate limiter
├── benchmarks/
│   └── benchmark.py        # Throughput, latency, memory benchmarks
├── cpp/
│   └── benchmark.cpp       # C++ unordered_map comparison benchmark
└── data/                   # Runtime data (gitignored)
    ├── wal.log
    └── sst/
```

## Design Decisions

**Lazy TTL eviction** — keys are checked for expiry on access rather than via a background scanner. This matches Redis's default strategy and eliminates sweep overhead entirely.

**Absolute expiry timestamps in WAL** — the WAL logs the absolute deadline (`expiry=1699999999.0`), not the relative TTL (`ttl=5`). A relative TTL written at 9am would be meaningless if replayed at 11am after a crash.

**Idempotent WAL replay** — every WAL entry carries an integer op ID. Replay tracks seen IDs and skips duplicates, making crash recovery safe to run multiple times.

**Fixed-window rate limiter** — key pattern `rate:{user}:{window_id}` where `window_id = int(time.time() // window_seconds)`. The counter key changes automatically when the window rolls over — no cleanup needed. O(1) time and space.

**SSTable in-memory index** — on open, the SSTable scans the file once to build a `{key: byte_offset}` dict. Every subsequent lookup is `seek(offset)` + one `readline()` — O(1) regardless of file size.

**Buffered WAL writes** — lines are accumulated in a list and flushed as one write call every N operations. This reduces write syscalls from N to N/sync_every, trading a small durability window for significantly higher throughput.

## Stack

- Python 3.8+ — core engine, standard library only (no external dependencies)
- C++ 17 (g++) — standalone benchmark for performance comparison
