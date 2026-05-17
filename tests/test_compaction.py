from __future__ import annotations
import os
import time
from core.memtable import MemTable
from core.sstable import SSTable
from core.compaction import compact


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
