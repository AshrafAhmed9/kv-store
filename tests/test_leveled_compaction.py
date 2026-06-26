from __future__ import annotations
import os
from core.memtable import MemTable
from core.sstable import SSTable
from core.leveled_compaction import LeveledCompactor


def _flush(keys: list[tuple[str, str]], path: str) -> str:
    mt = MemTable()
    for k, v in keys:
        mt.set(k, v)
    SSTable.flush(mt.items(), path)
    return path


def test_l0_compacts_into_l1(tmp_path):
    sst_dir = str(tmp_path / "sst")
    os.makedirs(sst_dir)
    compactor = LeveledCompactor(sst_dir, l0_threshold=2)

    _flush([("a", "1"), ("b", "2")], os.path.join(sst_dir, "f1.sst"))
    compactor.add_flush(os.path.join(sst_dir, "f1.sst"))

    _flush([("c", "3"), ("d", "4")], os.path.join(sst_dir, "f2.sst"))
    compactor.add_flush(os.path.join(sst_dir, "f2.sst"))

    _flush([("e", "5"), ("f", "6")], os.path.join(sst_dir, "f3.sst"))
    compactor.add_flush(os.path.join(sst_dir, "f3.sst"))

    summary = compactor.level_summary()
    assert 1 in summary, "data should have been pushed to L1"
    assert summary.get(0, 0) <= 2, "L0 should be drained after compaction"


def test_newest_value_wins_across_levels(tmp_path):
    sst_dir = str(tmp_path / "sst")
    os.makedirs(sst_dir)
    compactor = LeveledCompactor(sst_dir, l0_threshold=2)

    _flush([("key", "old")], os.path.join(sst_dir, "f1.sst"))
    compactor.add_flush(os.path.join(sst_dir, "f1.sst"))

    _flush([("key", "new")], os.path.join(sst_dir, "f2.sst"))
    compactor.add_flush(os.path.join(sst_dir, "f2.sst"))

    _flush([("pad", "x")], os.path.join(sst_dir, "f3.sst"))
    compactor.add_flush(os.path.join(sst_dir, "f3.sst"))

    all_files = compactor.all_sstables()
    found = None
    for path in all_files:
        sst = SSTable(path)
        val = sst.get("key")
        if val is not None:
            found = val
    assert found == "new"


def test_all_keys_survive_compaction(tmp_path):
    sst_dir = str(tmp_path / "sst")
    os.makedirs(sst_dir)
    compactor = LeveledCompactor(sst_dir, l0_threshold=2)

    for i in range(6):
        path = os.path.join(sst_dir, f"f{i}.sst")
        _flush([(f"k{i}", f"v{i}")], path)
        compactor.add_flush(path)

    all_files = compactor.all_sstables()
    all_keys = set()
    for path in all_files:
        sst = SSTable(path)
        all_keys.update(sst.keys())

    for i in range(6):
        assert f"k{i}" in all_keys, f"k{i} lost during compaction"


def test_compaction_count_increases(tmp_path):
    sst_dir = str(tmp_path / "sst")
    os.makedirs(sst_dir)
    compactor = LeveledCompactor(sst_dir, l0_threshold=2)

    for i in range(5):
        path = os.path.join(sst_dir, f"f{i}.sst")
        _flush([(f"k{i}", f"v{i}")], path)
        compactor.add_flush(path)

    assert compactor.compaction_count > 0
    assert compactor.bytes_written > 0
