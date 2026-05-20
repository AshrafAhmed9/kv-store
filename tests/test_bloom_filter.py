from __future__ import annotations
from core.bloom_filter import BloomFilter


def test_added_key_always_found():
    bf = BloomFilter()
    bf.add("hello")
    assert bf.might_contain("hello") is True

def test_missing_key_usually_absent():
    bf = BloomFilter(size=1024, num_hashes=3)
    # with a large filter and few keys, missing keys return False
    assert bf.might_contain("definitely_not_here") is False

def test_no_false_negatives():
    bf = BloomFilter.for_capacity(100)
    keys = [f"key:{i}" for i in range(100)]
    for k in keys:
        bf.add(k)
    # every added key must be found — false negatives are impossible
    for k in keys:
        assert bf.might_contain(k) is True

def test_for_capacity_sizes_correctly():
    bf = BloomFilter.for_capacity(1000, fp_rate=0.01)
    assert bf._size > 0
    assert bf._num_hashes > 0
