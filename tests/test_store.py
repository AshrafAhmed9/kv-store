from __future__ import annotations
import threading
import time
import pytest
from core.store import KVStore


def test_set_and_get():
    store = KVStore()
    store.set("key", "value")
    assert store.get("key") == "value"

def test_get_missing_returns_none():
    assert KVStore().get("missing") is None

def test_delete():
    store = KVStore()
    store.set("key", "value")
    assert store.delete("key") is True
    assert store.get("key") is None

def test_delete_missing_returns_false():
    assert KVStore().delete("missing") is False

def test_ttl_expiry():
    store = KVStore()
    store.set("key", "value", ttl=0.1)
    assert store.get("key") == "value"
    time.sleep(0.2)
    assert store.get("key") is None

def test_no_ttl_does_not_expire():
    store = KVStore()
    store.set("key", "value")
    time.sleep(0.1)
    assert store.get("key") == "value"

def test_incr_new_key_starts_at_one():
    assert KVStore().incr("counter") == 1

def test_incr_existing_key():
    store = KVStore()
    store.set("counter", "5")
    assert store.incr("counter") == 6

def test_incr_expired_key_resets():
    store = KVStore()
    store.set("counter", "5", ttl=0.1)
    time.sleep(0.2)
    assert store.incr("counter") == 1

def test_keys_excludes_expired():
    store = KVStore()
    store.set("alive", "1")
    store.set("dead", "2", ttl=0.1)
    time.sleep(0.2)
    assert store.keys() == ["alive"]

def test_concurrent_writes_no_errors():
    store = KVStore()
    errors = []

    def writer(n):
        try:
            for i in range(100):
                store.set(f"k{n}:{i}", str(i))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert not errors
    assert len(store.keys()) == 1000

def test_concurrent_reads_and_writes():
    store = KVStore()
    for i in range(100):
        store.set(f"k{i}", str(i))
    errors = []

    def reader():
        try:
            for i in range(100): store.get(f"k{i}")
        except Exception as e:
            errors.append(e)

    def writer():
        try:
            for i in range(100): store.set(f"new{i}", str(i))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=reader) for _ in range(5)]
    threads += [threading.Thread(target=writer) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors
