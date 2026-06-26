from __future__ import annotations
import os
import time


def _key_range(path: str) -> tuple[str, str]:
    """Read min and max keys from an SSTable file without loading it fully."""
    keys = []
    with open(path, "rb") as f:
        for line in f:
            key = line.decode("utf-8").split("\t", 1)[0]
            keys.append(key)
    return (keys[0], keys[-1]) if keys else ("", "")


def _overlapping(min_key: str, max_key: str, entries: list[dict]) -> list[dict]:
    """Find entries whose key range overlaps [min_key, max_key]."""
    return [e for e in entries if not (e["max"] < min_key or e["min"] > max_key)]


class LeveledCompactor:
    """Leveled compaction: SSTables organized into levels.

    L0: receives memtable flushes, files may have overlapping key ranges.
    L1+: files within each level have non-overlapping key ranges.

    When L0 fills up, ALL L0 files merge into L1 (because L0 ranges overlap).
    When L1+ fills up, the OLDEST file merges with overlapping files in L(N+1).
    This bounds space amplification and gives predictable read cost.
    """

    def __init__(self, sst_dir: str, l0_threshold: int = 4):
        self._sst_dir = sst_dir
        self._l0_threshold = l0_threshold
        self._levels: dict[int, list[dict]] = {0: []}
        self._counter = 0
        self.bytes_written = 0
        self.compaction_count = 0

    def add_flush(self, sst_path: str) -> None:
        min_k, max_k = _key_range(sst_path)
        self._levels[0].append({"path": sst_path, "min": min_k, "max": max_k})
        self._maybe_compact()

    def _maybe_compact(self) -> None:
        level = 0
        while level in self._levels and len(self._levels[level]) > self._l0_threshold:
            self._compact_level(level)
            level += 1

    def _compact_level(self, level: int) -> None:
        next_level = level + 1
        if next_level not in self._levels:
            self._levels[next_level] = []

        if level == 0:
            sources = list(self._levels[level])
        else:
            sources = [self._levels[level][0]]

        source_paths = [e["path"] for e in sources]
        all_min = min(e["min"] for e in sources)
        all_max = max(e["max"] for e in sources)
        targets = _overlapping(all_min, all_max, self._levels[next_level])
        target_paths = [e["path"] for e in targets]

        all_paths = source_paths + target_paths

        merged: dict[str, tuple[str, float]] = {}
        for path in all_paths:
            with open(path, "rb") as f:
                for line in f:
                    parts = line.decode("utf-8").rstrip("\n").split("\t")
                    if len(parts) != 3:
                        continue
                    key, value, expiry_str = parts
                    merged[key] = (value, float(expiry_str))

        now = time.time()
        self._counter += 1
        output_path = os.path.join(
            self._sst_dir, f"L{next_level}_{time.time_ns()}_{self._counter:04d}.sst"
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        written = 0
        with open(output_path, "wb") as out:
            for key in sorted(merged):
                value, expiry = merged[key]
                if value == "__tombstone__":
                    continue
                if expiry and now > expiry:
                    continue
                line = f"{key}\t{value}\t{expiry}\n"
                data = line.encode("utf-8")
                out.write(data)
                written += len(data)

        self.bytes_written += written
        self.compaction_count += 1

        source_path_set = set(source_paths)
        target_path_set = set(target_paths)
        self._levels[level] = [e for e in self._levels[level] if e["path"] not in source_path_set]
        self._levels[next_level] = [e for e in self._levels[next_level] if e["path"] not in target_path_set]

        min_k, max_k = _key_range(output_path)
        self._levels[next_level].append({"path": output_path, "min": min_k, "max": max_k})

        for path in all_paths:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    def all_sstables(self) -> list[str]:
        result = []
        for level in sorted(self._levels.keys()):
            for entry in self._levels[level]:
                result.append(entry["path"])
        return result

    def level_summary(self) -> dict[int, int]:
        return {level: len(files) for level, files in self._levels.items() if files}
