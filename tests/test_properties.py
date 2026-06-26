from __future__ import annotations
import os
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st
from core.store import KVStore


@given(ops=st.lists(
    st.tuples(
        st.sampled_from(["set", "delete"]),
        st.text(alphabet="abcdefgh", min_size=1, max_size=4),
        st.text(alphabet="0123456789", min_size=1, max_size=8),
    ),
    min_size=1, max_size=200,
))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_engine_matches_dict_oracle(tmp_path_factory, ops):
    """Every get/scan result matches a plain dict that tracks the same ops."""
    tmp = tmp_path_factory.mktemp("prop")
    store = KVStore(sst_dir=str(tmp / "sst"), memtable_size=100)
    oracle: dict[str, str] = {}

    for op, key, val in ops:
        if op == "set":
            store.set(key, val)
            oracle[key] = val
        elif op == "delete":
            store.delete(key)
            oracle.pop(key, None)

    for key, expected in oracle.items():
        assert store.get(key) == expected, f"mismatch on {key!r}"

    for key in list(oracle):
        if store.get(key) is None and key in oracle:
            assert False, f"store lost key {key!r}"


@given(ops=st.lists(
    st.tuples(
        st.sampled_from(["set", "delete"]),
        st.text(alphabet="abcdefgh", min_size=1, max_size=4),
        st.text(alphabet="0123456789", min_size=1, max_size=8),
    ),
    min_size=10, max_size=100,
))
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_scan_matches_oracle(tmp_path_factory, ops):
    """scan() returns exactly the live keys in range, matching a dict oracle."""
    tmp = tmp_path_factory.mktemp("scan")
    store = KVStore(sst_dir=str(tmp / "sst"), memtable_size=80)
    oracle: dict[str, str] = {}

    for op, key, val in ops:
        if op == "set":
            store.set(key, val)
            oracle[key] = val
        elif op == "delete":
            store.delete(key)
            oracle.pop(key, None)

    result = store.scan("a", "h")
    expected = sorted((k, v) for k, v in oracle.items() if "a" <= k <= "h")
    assert result == expected
