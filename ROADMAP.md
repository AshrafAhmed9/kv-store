# Roadmap

This project is an educational storage engine. The following are honest
areas for future exploration — not commitments.

## Completed

**Bloom filters** ✅ implemented in v0.2.0
Each SSTable carries an in-memory Bloom Filter sized for 1% false positive rate.
Misses skip disk entirely — false negatives are impossible by design.

**Automatic compaction** ✅ implemented in v2
Compaction now triggers automatically when the SSTable count exceeds a
configurable threshold (default 4), merging via crash-safe atomic rename.
v2 also added a leveled compaction implementation with a benchmark measuring
write amplification against the size-tiered default.

**WAL rotation** ✅ implemented in v2
After each durable SSTable flush, the WAL starts a new segment and deletes
old ones — replay on restart is bounded to un-flushed data only.

## Potential improvements

**Block cache**
SSTables currently open a file handle per lookup. A block cache would keep
recently read SSTable blocks in memory, reducing disk I/O on hot keys.
Low priority: hot keys are already served from the MemTable, so this only
helps repeated reads of older, flushed data.

**Replication (conceptual)**
A leader/follower model where the WAL is streamed to a follower node.
This would introduce ordering, consistency, and failover challenges.

## Out of scope
- Distributed consensus (Raft/Paxos)
- Sharding
- Authentication
