import pytest
from kvstore.config import Config, load


def _valid(**over):
    base = dict(data_dir="data", memtable_size=1024, sync_every=1,
                compaction_trigger=4, bloom_fp_rate=0.01,
                server_host="127.0.0.1", server_port=6379)
    base.update(over)
    return Config(**base)


def test_paths_derived():
    c = _valid(data_dir="d")
    assert c.wal_path.endswith("wal")
    assert c.sst_dir.endswith("sst")


@pytest.mark.parametrize("bad", [
    {"memtable_size": 0},
    {"sync_every": 0},
    {"bloom_fp_rate": 1.5},
    {"compaction_trigger": 0},
])
def test_validation_rejects(bad):
    with pytest.raises(ValueError):
        _valid(**bad)


def test_load_defaults():
    assert load().sync_every >= 1
