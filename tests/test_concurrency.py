from __future__ import annotations
import threading
from core.store import KVStore


def test_concurrent_set_get_delete_no_crash(tmp_path):
    """Many threads interleaving ops while flushes run — no crashes, no lost final state."""
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=200)
    errors = []
    n_threads = 8
    n_ops = 200

    def worker(tid):
        try:
            for i in range(n_ops):
                key = f"t{tid}_k{i}"
                store.set(key, f"v{i}")
                store.get(key)
                if i % 5 == 0:
                    store.delete(key)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"threads raised: {errors}"

    for tid in range(n_threads):
        for i in range(n_ops):
            key = f"t{tid}_k{i}"
            val = store.get(key)
            if i % 5 == 0:
                assert val is None, f"{key} should be deleted"
            else:
                assert val == f"v{i}", f"{key} expected v{i}, got {val}"


def test_concurrent_scan_during_writes(tmp_path):
    """Scans return consistent results while writes are happening."""
    sst_dir = str(tmp_path / "sst")
    store = KVStore(sst_dir=sst_dir, memtable_size=1024 * 1024)

    errors = []

    for i in range(50):
        store.set(f"key_{i:04d}", f"val{i}")

    def writer():
        try:
            for i in range(50, 150):
                store.set(f"key_{i:04d}", f"val{i}")
        except Exception as e:
            errors.append(e)

    def scanner():
        try:
            for _ in range(20):
                result = store.scan("key_0000", "key_9999")
                for k, v in result:
                    assert k.startswith("key_"), f"bad key {k}"
                    assert v.startswith("val"), f"bad value {v}"
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(3)]
    threads += [threading.Thread(target=scanner) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"threads raised: {errors}"
