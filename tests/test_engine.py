from __future__ import annotations
import os
import time
from core.store import KVStore


def test_read_from_sstable_after_flush(tmp_path):
    """Key flushed to SSTable is still readable — proves the disk path works."""
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=50)

    store.set("key1", "value1")
    store.set("key2", "value2")
    store.set("key3", "a]longer_value_that_triggers_flush")

    sst_files = os.listdir(sst_dir) if os.path.isdir(sst_dir) else []
    assert len(sst_files) >= 1, "flush should have created an SSTable"

    assert store.get("key1") == "value1"
    assert store.get("key2") == "value2"


def test_newer_memtable_shadows_older_sstable(tmp_path):
    """A write in the memtable beats an older value on disk."""
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=50)

    store.set("key", "old_value_padding_for_flush")
    store.set("key", "old_value_padding_for_flush2")

    store.set("key", "new")
    assert store.get("key") == "new"


def test_tombstone_masks_sstable_value(tmp_path):
    """A delete in the memtable hides a value flushed to disk."""
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=50)

    store.set("key", "value_with_enough_padding_to_flush")
    store.set("pad", "more_padding_to_force_the_flush_now")

    store.delete("key")
    assert store.get("key") is None
def test_key_found_in_oldest_sstable(tmp_path):
    """A key only in the oldest SSTable is still reachable."""
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=50)

    store.set("alpha", "first_value_alpha_padding_here")
    store.set("beta", "second_value_beta_padding_here!")

    store.set("gamma", "third_value_gamma_padding_here")
    store.set("delta", "fourth_value_delta_padding_here")

    assert store.get("alpha") == "first_value_alpha_padding_here"
    assert store.get("gamma") == "third_value_gamma_padding_here"

def test_keys_spans_all_tiers(tmp_path):
    """keys() returns keys from memtable AND SSTables, deduped."""
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=50)

    store.set("flushed", "value_padded_enough_to_trigger")
    store.set("pad", "more_padding_to_trigger_a_flush")

    store.set("live", "in_memtable")

    all_keys = store.keys()
    assert "flushed" in all_keys
    assert "live" in all_keys


def test_sstables_loaded_on_restart(tmp_path):
    """A new KVStore picks up SSTables written by a previous instance."""
    sst_dir = str(tmp_path / "sst")

    store1 = KVStore(sst_dir=sst_dir, memtable_size=50)
    store1.set("key", "value_padded_to_force_a_flush!!")
    store1.set("pad", "more_padding_to_force_the_flush")

    assert os.listdir(sst_dir), "SSTable should exist on disk"

    store2 = KVStore(sst_dir=sst_dir)
    assert store2.get("key") == "value_padded_to_force_a_flush!!"
