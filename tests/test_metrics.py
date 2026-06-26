from __future__ import annotations
from core.metrics import Metrics


def test_counters_increment():
    m = Metrics()
    m.record_read()
    m.record_read()
    m.record_write()
    m.record_delete()
    m.record_compaction(0.5)
    m.record_corrupt_record()

    s = m.snapshot(key_count=10)
    assert s["reads"] == 2
    assert s["writes"] == 1
    assert s["deletes"] == 1
    assert s["compactions_total"] == 1
    assert s["compaction_seconds"] == 0.5
    assert s["corrupt_records"] == 1


def test_prometheus_format():
    m = Metrics()
    m.record_read()
    m.record_write()

    text = m.prometheus(key_count=5, memtable_size=1024,
                        sstable_count=2, wal_segment_count=1)

    assert "# TYPE kvstore_reads_total counter" in text
    assert "kvstore_reads_total 1" in text
    assert "kvstore_writes_total 1" in text
    assert "kvstore_key_count 5" in text
    assert "kvstore_memtable_size_bytes 1024" in text
    assert "kvstore_sstable_count 2" in text
    assert text.endswith("\n")
