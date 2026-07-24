from __future__ import annotations
import time
from kvstore.memtable import MemTable


def test_set_and_get():
    mem = MemTable()
    mem.set("key", "value")
    assert mem.get("key") == "value"

def test_delete_returns_none_but_has_key_stays_true():
    """A tombstone means get() is None but has_key() is still True — that's
    what tells KVStore to stop checking older tiers for this key."""
    mem = MemTable()
    mem.set("key", "value")
    mem.delete("key")
    assert mem.get("key") is None
    assert mem.has_key("key") is True

def test_expired_entry_returns_none():
    mem = MemTable()
    mem.set("key", "value", expiry=time.time() + 0.1)
    assert mem.get("key") == "value"
    time.sleep(0.2)
    assert mem.get("key") is None

def test_should_flush_once_size_limit_reached():
    mem = MemTable(size_limit=10)
    assert mem.should_flush is False
    mem.set("key", "a_value_much_longer_than_ten_bytes")
    assert mem.should_flush is True

def test_items_returns_sorted_key_order():
    mem = MemTable()
    mem.set("banana", "2")
    mem.set("apple", "1")
    keys = [k for k, _ in mem.items()]
    assert keys == ["apple", "banana"]
