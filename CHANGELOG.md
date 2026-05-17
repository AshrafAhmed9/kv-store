# Changelog

## [0.1.0] — 2026-05-17

### Added
- In-memory KVStore with GET, SET, DELETE, INCR, TTL
- Write-Ahead Log with idempotent replay and absolute expiry timestamps
- TCP server with line protocol (Redis-inspired)
- Session store and fixed-window rate limiter
- LSM-tree persistence: MemTable, SSTable with in-memory index, Compaction
- /metrics HTTP endpoint (reads, writes, key_count, uptime)
- Graceful shutdown on SIGINT and SIGTERM
- Structured logging with timestamps and log levels
- Docker and docker-compose support
- Environment-variable-based config (12-factor)
- 32 pytest tests with GitHub Actions CI
- C++ unordered_map benchmark for comparison
