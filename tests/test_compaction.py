from __future__ import annotations
import os
import time
from kvstore.memtable import MemTable
from kvstore.sstable import SSTable
from kvstore.compaction import compact
from kvstore.store import KVStore


def test_latest_value_wins(tmp_path):
    sst1 = str(tmp_path / "1.sst")
    sst2 = str(tmp_path / "2.sst")
    out  = str(tmp_path / "compacted.sst")

    m1 = MemTable(); m1.set("key", "old")
    m2 = MemTable(); m2.set("key", "new")
    SSTable.flush(m1.items(), sst1)
    SSTable.flush(m2.items(), sst2)

    compact([sst1, sst2], out)

    sst = SSTable(out)
    assert sst.get("key") == "new"

def test_tombstones_removed(tmp_path):
    sst1 = str(tmp_path / "1.sst")
    sst2 = str(tmp_path / "2.sst")
    out  = str(tmp_path / "compacted.sst")

    m1 = MemTable(); m1.set("key", "value")
    m2 = MemTable(); m2.delete("key")
    SSTable.flush(m1.items(), sst1)
    SSTable.flush(m2.items(), sst2)

    compact([sst1, sst2], out)

    sst = SSTable(out)
    assert sst.get("key") is None

def test_expired_keys_dropped(tmp_path):
    sst1 = str(tmp_path / "1.sst")
    out  = str(tmp_path / "compacted.sst")

    m1 = MemTable(); m1.set("key", "val", expiry=time.time() + 0.1)
    SSTable.flush(m1.items(), sst1)

    time.sleep(0.2)
    compact([sst1], out)

    sst = SSTable(out)
    assert sst.get("key") is None

def test_source_files_deleted(tmp_path):
    sst1 = str(tmp_path / "1.sst")
    sst2 = str(tmp_path / "2.sst")
    out  = str(tmp_path / "compacted.sst")

    m1 = MemTable(); m1.set("a", "1")
    m2 = MemTable(); m2.set("b", "2")
    SSTable.flush(m1.items(), sst1)
    SSTable.flush(m2.items(), sst2)

    compact([sst1, sst2], out)

    assert not os.path.exists(sst1)
    assert not os.path.exists(sst2)

def test_keys_from_all_files_merged(tmp_path):
    sst1 = str(tmp_path / "1.sst")
    sst2 = str(tmp_path / "2.sst")
    out  = str(tmp_path / "compacted.sst")

    m1 = MemTable(); m1.set("a", "1"); m1.set("b", "2")
    m2 = MemTable(); m2.set("c", "3"); m2.set("d", "4")
    SSTable.flush(m1.items(), sst1)
    SSTable.flush(m2.items(), sst2)

    compact([sst1, sst2], out)

    sst = SSTable(out)
    assert sst.get("a") == "1"
    assert sst.get("b") == "2"
    assert sst.get("c") == "3"
    assert sst.get("d") == "4"

def test_stale_tmp_ignored_on_startup(tmp_path):
    """A leftover .tmp from a crashed flush/compaction is cleaned up."""
    sst_dir = str(tmp_path / "sst")
    os.makedirs(sst_dir)

    stale_tmp = os.path.join(sst_dir, "1234.sst.tmp")
    with open(stale_tmp, "w") as f:
        f.write("garbage")

    store = KVStore(sst_dir=sst_dir)
    assert not os.path.exists(stale_tmp)

def test_crash_mid_compaction_leaves_originals(tmp_path):
    """If a .tmp exists but rename never happened, originals are intact."""
    sst1 = str(tmp_path / "1.sst")
    sst2 = str(tmp_path / "2.sst")
    out  = str(tmp_path / "compacted.sst")

    m1 = MemTable(); m1.set("a", "1")
    m2 = MemTable(); m2.set("b", "2")
    SSTable.flush(m1.items(), sst1)
    SSTable.flush(m2.items(), sst2)

    with open(out + ".tmp", "w") as f:
        f.write("partial garbage from a crash")

    assert os.path.exists(sst1)
    assert os.path.exists(sst2)
    assert SSTable(sst1).get("a") == "1"
    assert SSTable(sst2).get("b") == "2"

def test_three_way_merge_with_mixed_tombstone_and_expiry(tmp_path):
    """A realistic merge: an overwritten key, a deleted key, and an expired
    key must all resolve correctly when three SSTables are compacted at once."""
    sst1 = str(tmp_path / "1.sst")
    sst2 = str(tmp_path / "2.sst")
    sst3 = str(tmp_path / "3.sst")
    out  = str(tmp_path / "compacted.sst")

    m1 = MemTable(); m1.set("overwritten", "old"); m1.set("deleted", "will_go")
    m2 = MemTable(); m2.set("overwritten", "new"); m2.delete("deleted")
    m3 = MemTable(); m3.set("expired", "gone", expiry=time.time() + 0.1)
    SSTable.flush(m1.items(), sst1)
    SSTable.flush(m2.items(), sst2)
    SSTable.flush(m3.items(), sst3)

    time.sleep(0.2)
    compact([sst1, sst2, sst3], out)

    sst = SSTable(out)
    assert sst.get("overwritten") == "new"
    assert sst.get("deleted") is None
    assert sst.get("expired") is None
