# Roadmap

This project is an educational storage engine. The following are honest
areas for future exploration — not commitments.

## Potential improvements

**Automatic compaction**
Currently compaction is triggered manually. A background thread that monitors
SSTable count and triggers compaction automatically would match production behavior.

**Bloom filters**
Before checking an SSTable for a key that doesn't exist, a bloom filter would
allow an O(1) probabilistic check — avoiding unnecessary disk reads on misses.

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
