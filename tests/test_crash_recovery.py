from __future__ import annotations
import os
from core.store import KVStore
from core.wal import WAL


def test_recovery_after_unclean_shutdown(tmp_path):
    """Simulate a crash: write data, don't call close(), reopen and verify."""
    wal_dir = str(tmp_path / "wal")
    sst_dir = str(tmp_path / "sst")

    wal = WAL(wal_dir, sync_every=1)
    store = KVStore(wal=wal, sst_dir=sst_dir)
    for i in range(50):
        store.set(f"key{i}", f"value{i}")
    wal.sync()
    # NO wal.close() — simulating a crash

    wal2 = WAL(wal_dir)
    store2 = KVStore(wal=wal2, sst_dir=sst_dir)
    for i in range(50):
        assert store2.get(f"key{i}") == f"value{i}"
    wal2.close()


def test_torn_write_is_skipped(tmp_path):
    """A partial last record (simulating mid-write crash) is safely skipped."""
    wal_dir = str(tmp_path / "wal")
    sst_dir = str(tmp_path / "sst")

    wal = WAL(wal_dir, sync_every=1)
    store = KVStore(wal=wal, sst_dir=sst_dir)
    store.set("good", "survives")
    wal.sync()

    seg_files = sorted(os.listdir(wal_dir))
    last_seg = os.path.join(wal_dir, seg_files[-1])
    with open(last_seg, "a") as f:
        f.write('{"op_id": 999, "op": "SET", "key": "torn", "val')

    wal2 = WAL(wal_dir)
    store2 = KVStore(wal=wal2, sst_dir=sst_dir)
    assert store2.get("good") == "survives"
    assert store2.get("torn") is None
    wal2.close()


def test_rotation_deletes_old_segments(tmp_path):
    """After flush + rotate, old WAL segments are removed."""
    wal_dir = str(tmp_path / "wal")
    sst_dir = str(tmp_path / "sst")

    wal = WAL(wal_dir, sync_every=1)
    store = KVStore(wal=wal, sst_dir=sst_dir, memtable_size=50)

    store.set("key1", "value1_with_enough_padding_to_flush")
    store.set("key2", "value2_with_enough_padding_to_flush")

    seg_files = [f for f in os.listdir(wal_dir) if f.endswith(".log")]
    assert len(seg_files) == 1, "only the current segment should remain after rotation"


def test_recovery_after_flush_and_rotation(tmp_path):
    """Data survives restart even when its WAL segment was rotated away,
    because the data is in an SSTable."""
    wal_dir = str(tmp_path / "wal")
    sst_dir = str(tmp_path / "sst")

    wal = WAL(wal_dir, sync_every=1)
    store = KVStore(wal=wal, sst_dir=sst_dir, memtable_size=50)

    store.set("flushed", "safely_in_sstable_padding_here")
    store.set("pad", "force_flush_padding_value_here!!")
    store.set("after", "in_wal_only")
    wal.close()

    wal2 = WAL(wal_dir)
    store2 = KVStore(wal=wal2, sst_dir=sst_dir)
    assert store2.get("flushed") == "safely_in_sstable_padding_here"
    assert store2.get("after") == "in_wal_only"
    wal2.close()
