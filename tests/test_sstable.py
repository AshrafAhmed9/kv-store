from __future__ import annotations
import time
from kvstore.memtable import MemTable
from kvstore.sstable import SSTable


def test_flush_and_get(tmp_path):
    mem = MemTable()
    mem.set("apple", "1")
    mem.set("banana", "2")
    sst = SSTable.flush(mem.items(), str(tmp_path / "t.sst"))
    assert sst.get("apple") == "1"
    assert sst.get("banana") == "2"
    assert sst.get("missing") is None

def test_tombstone_returns_none(tmp_path):
    mem = MemTable()
    mem.set("key", "value")
    mem.delete("key")
    sst = SSTable.flush(mem.items(), str(tmp_path / "t.sst"))
    assert sst.get("key") is None

def test_expired_entry_returns_none(tmp_path):
    mem = MemTable()
    mem.set("short", "val", expiry=time.time() + 0.1)
    sst = SSTable.flush(mem.items(), str(tmp_path / "t.sst"))
    assert sst.get("short") == "val"
    time.sleep(0.2)
    assert sst.get("short") is None

def test_index_correctness(tmp_path):
    mem = MemTable()
    for i in range(20):
        mem.set(f"key{i}", f"val{i}")
    sst = SSTable.flush(mem.items(), str(tmp_path / "t.sst"))
    for i in range(20):
        assert sst.get(f"key{i}") == f"val{i}"

def test_persistence_across_reopen(tmp_path):
    path = str(tmp_path / "t.sst")
    mem = MemTable()
    mem.set("persist", "yes")
    SSTable.flush(mem.items(), path)

    sst2 = SSTable(path)            # reopen — rebuilds index from file
    assert sst2.get("persist") == "yes"

def test_range_scan_marks_tombstone_as_none(tmp_path):
    """range_scan surfaces tombstones as (key, None) so a caller merging
    tiers knows this key was deleted, not just absent from this file."""
    mem = MemTable()
    mem.set("a", "1")
    mem.delete("b")
    sst = SSTable.flush(mem.items(), str(tmp_path / "t.sst"))
    result = dict(sst.range_scan("a", "b"))
    assert result["a"] == "1"
    assert result["b"] is None
