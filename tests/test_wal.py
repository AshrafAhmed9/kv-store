from __future__ import annotations
import time
from core.store import KVStore
from core.wal import WAL
import os


def test_basic_recovery(tmp_path):
    wal_dir = str(tmp_path / "wal")
    sst_dir = str(tmp_path / "sst")
    wal = WAL(wal_dir)
    store = KVStore(wal=wal, sst_dir=sst_dir)
    store.set("name", "Alice")
    wal.close()

    wal2 = WAL(wal_dir)
    store2 = KVStore(wal=wal2, sst_dir=sst_dir)
    assert store2.get("name") == "Alice"
    wal2.close()

def test_delete_survives_restart(tmp_path):
    wal_dir = str(tmp_path / "wal")
    sst_dir = str(tmp_path / "sst")
    wal = WAL(wal_dir)
    store = KVStore(wal=wal, sst_dir=sst_dir)
    store.set("key", "value")
    store.delete("key")
    wal.close()

    wal2 = WAL(wal_dir)
    store2 = KVStore(wal=wal2, sst_dir=sst_dir)
    assert store2.get("key") is None
    wal2.close()

def test_expired_key_not_restored(tmp_path):
    wal_dir = str(tmp_path / "wal")
    sst_dir = str(tmp_path / "sst")
    wal = WAL(wal_dir)
    store = KVStore(wal=wal, sst_dir=sst_dir)
    store.set("temp", "gone", ttl=0.1)
    wal.close()

    time.sleep(0.2)
    wal2 = WAL(wal_dir)
    store2 = KVStore(wal=wal2, sst_dir=sst_dir)
    assert store2.get("temp") is None
    wal2.close()

def test_corrupt_lines_skipped(tmp_path):
    wal_dir = str(tmp_path / "wal")
    sst_dir = str(tmp_path / "sst")
    wal = WAL(wal_dir)
    store = KVStore(wal=wal, sst_dir=sst_dir)
    store.set("good", "value")
    wal.sync()

    seg_files = sorted(os.listdir(wal_dir))
    with open(os.path.join(wal_dir, seg_files[-1]), "a") as f:
        f.write("this is not valid json\n")
    wal.close()

    wal2 = WAL(wal_dir)
    store2 = KVStore(wal=wal2, sst_dir=sst_dir)
    assert store2.get("good") == "value"
    wal2.close()

def test_idempotent_replay(tmp_path):
    wal_dir = str(tmp_path / "wal")
    sst_dir = str(tmp_path / "sst")
    wal = WAL(wal_dir)
    store = KVStore(wal=wal, sst_dir=sst_dir)
    store.set("key", "value")
    wal.close()

    wal2 = WAL(wal_dir)
    store2 = KVStore(wal=wal2, sst_dir=sst_dir)
    wal2.replay(store2)
    assert store2.get("key") == "value"
    wal2.close()
