from __future__ import annotations
from kvstore.bloom_filter import BloomFilter


def test_added_key_always_found():
    bf = BloomFilter()
    bf.add("hello")
    assert bf.might_contain("hello") is True

def test_missing_key_usually_absent():
    bf = BloomFilter(size=1024, num_hashes=3)
    assert bf.might_contain("definitely_not_here") is False

def test_no_false_negatives():
    bf = BloomFilter.for_capacity(100)
    keys = [f"key:{i}" for i in range(100)]
    for k in keys:
        bf.add(k)
    for k in keys:
        assert bf.might_contain(k) is True

def test_for_capacity_sizes_correctly():
    bf = BloomFilter.for_capacity(1000, fp_rate=0.01)
    assert bf._size > 0
    assert bf._num_hashes > 0

def test_false_positive_rate_within_target():
    """Insert N keys, query M absent keys, verify FP rate stays near 1%."""
    n = 10_000
    m = 50_000
    bf = BloomFilter.for_capacity(n, fp_rate=0.01)

    for i in range(n):
        bf.add(f"present:{i}")

    false_positives = sum(
        1 for i in range(m) if bf.might_contain(f"absent:{i}")
    )
    fp_rate = false_positives / m

    assert fp_rate < 0.02, f"FP rate {fp_rate:.4f} exceeds 2% tolerance"
