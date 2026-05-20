from __future__ import annotations
import hashlib
import math


class BloomFilter:
    def __init__(self, size: int = 512, num_hashes: int = 3):
        self._size      = size
        self._num_hashes = num_hashes
        self._bits      = bytearray(size)

    @classmethod
    def for_capacity(cls, n: int, fp_rate: float = 0.01) -> BloomFilter:
        """Size the filter for n expected keys at a given false-positive rate."""
        if n == 0:
            return cls()
        m = max(int(-n * math.log(fp_rate) / (math.log(2) ** 2)), 64)
        k = max(int((m / n) * math.log(2)), 1)
        return cls(size=m, num_hashes=k)

    def _positions(self, key: str):
        for seed in range(self._num_hashes):
            digest = hashlib.sha256(f"{seed}:{key}".encode()).digest()
            yield int.from_bytes(digest[:4], "big") % self._size

    def add(self, key: str) -> None:
        for pos in self._positions(key):
            self._bits[pos] = 1

    def might_contain(self, key: str) -> bool:
        return all(self._bits[pos] for pos in self._positions(key))
