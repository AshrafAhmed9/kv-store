# Roadmap

This project is an educational storage engine. The following are honest
areas for future exploration — not commitments.

## Potential improvements

**Automatic compaction**
Currently compaction is triggered manually. A background thread that monitors
SSTable count and triggers compaction automatically would match production behavior.

**Bloom filters** ✅ implemented in v0.2.0
Each SSTable carries an in-memory Bloom Filter sized for 1% false positive rate.
Misses skip disk entirely — false negatives are impossible by design.

**Block cache**
SSTables currently open a file handle per lookup. A block cache would keep
recently read SSTable blocks in memory, reducing disk I/O on hot keys.

**WAL rotation**
The WAL grows indefinitely. After a successful SSTable flush, old WAL entries
could be truncated — matching how production engines handle log rotation.

**Replication (conceptual)**
A leader/follower model where the WAL is streamed to a follower node.
This would introduce ordering, consistency, and failover challenges.

## Out of scope
- Distributed consensus (Raft/Paxos)
- Sharding
- Authentication
