from __future__ import annotations
import time
from core.store import KVStore
from features.rate_limiter import RateLimiter


def test_allows_within_limit():
    store = KVStore()
    limiter = RateLimiter(store, limit=3, window=60)
    for _ in range(3):
        assert limiter.is_allowed("user") is True

def test_blocks_over_limit():
    store = KVStore()
    limiter = RateLimiter(store, limit=3, window=60)
    for _ in range(3): limiter.is_allowed("user")
    assert limiter.is_allowed("user") is False

def test_remaining_decrements():
    store = KVStore()
    limiter = RateLimiter(store, limit=5, window=60)
    assert limiter.remaining("user") == 5
    limiter.is_allowed("user")
    assert limiter.remaining("user") == 4

def test_users_are_independent():
    store = KVStore()
    limiter = RateLimiter(store, limit=2, window=60)
    limiter.is_allowed("alice")
    limiter.is_allowed("alice")
    assert limiter.is_allowed("alice") is False
    assert limiter.is_allowed("bob") is True   # bob unaffected

def test_window_resets():
    store = KVStore()
    limiter = RateLimiter(store, limit=2, window=1)
    limiter.is_allowed("user")
    limiter.is_allowed("user")
    assert limiter.is_allowed("user") is False
    time.sleep(1.1)
    assert limiter.is_allowed("user") is True  # new window, reset
