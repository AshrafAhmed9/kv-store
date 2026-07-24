from __future__ import annotations
from kvstore.store import KVStore


def test_scan_basic(tmp_path):
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir)

    store.set("apple", "1")
    store.set("banana", "2")
    store.set("cherry", "3")
    store.set("date", "4")

    result = store.scan("banana", "cherry")
    assert result == [("banana", "2"), ("cherry", "3")]


def test_scan_across_memtable_and_sstable(tmp_path):
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=50)

    store.set("aaa", "flushed_value_with_padding_here")
    store.set("bbb", "flushed_value_with_padding_here")

    store.set("ccc", "in_memtable")

    result = store.scan("aaa", "ccc")
    keys = [k for k, v in result]
    assert "aaa" in keys
    assert "ccc" in keys


def test_scan_newer_value_wins(tmp_path):
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=50)

    store.set("key", "old_value_padded_to_force_flush!")
    store.set("pad", "padding_to_actually_trigger_flush")

    store.set("key", "new")

    result = store.scan("key", "key")
    assert result == [("key", "new")]


def test_scan_excludes_tombstones(tmp_path):
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=50)

    store.set("key", "value_padded_to_force_flush_now!")
    store.set("pad", "padding_to_actually_trigger_flush")

    store.delete("key")

    result = store.scan("key", "key")
    assert result == []


def test_scan_empty_range(tmp_path):
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir)

    store.set("apple", "1")
    result = store.scan("mmm", "zzz")
    assert result == []
