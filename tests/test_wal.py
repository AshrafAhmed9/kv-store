from __future__ import annotations
import time
from core.store import KVStore
from core.wal import WAL


def test_basic_recovery(tmp_path):
    path = str(tmp_path / "wal.log")
    wal = WAL(path)
    store = KVStore(wal=wal)
    store.set("name", "Alice")
    wal.close()

    wal2 = WAL(path)
    store2 = KVStore(wal=wal2)
    assert store2.get("name") == "Alice"
    wal2.close()

def test_delete_survives_restart(tmp_path):
    path = str(tmp_path / "wal.log")
    wal = WAL(path)
    store = KVStore(wal=wal)
    store.set("key", "value")
    store.delete("key")
    wal.close()

    wal2 = WAL(path)
    store2 = KVStore(wal=wal2)
    assert store2.get("key") is None
    wal2.close()

def test_expired_key_not_restored(tmp_path):
    path = str(tmp_path / "wal.log")
    wal = WAL(path)
    store = KVStore(wal=wal)
    store.set("temp", "gone", ttl=0.1)
    wal.close()

    time.sleep(0.2)
    wal2 = WAL(path)
    store2 = KVStore(wal=wal2)
    assert store2.get("temp") is None   # expired during downtime
    wal2.close()

def test_corrupt_lines_skipped(tmp_path):
    path = str(tmp_path / "wal.log")
    wal = WAL(path)
    store = KVStore(wal=wal)
    store.set("good", "value")
    wal.close()

    with open(path, "a") as f:
        f.write("this is not valid json\n")

    wal2 = WAL(path)
    store2 = KVStore(wal=wal2)
    assert store2.get("good") == "value"
    wal2.close()

def test_idempotent_replay(tmp_path):
    path = str(tmp_path / "wal.log")
    wal = WAL(path)
    store = KVStore(wal=wal)
    store.set("key", "value")
    wal.close()

    wal2 = WAL(path)
    store2 = KVStore(wal=wal2)
    wal2.replay(store2)          # replay a second time
    assert store2.get("key") == "value"
    wal2.close()
