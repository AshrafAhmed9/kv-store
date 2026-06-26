from __future__ import annotations
import itertools
import json
import os
import time

class WAL:
    def __init__(self, directory: str, sync_every: int = 1):
        os.makedirs(directory, exist_ok=True)
        self._dir         = directory
        self._sync_every  = sync_every
        self._write_count = 0
        self._counter     = itertools.count(1)
        self._buffer: list[str] = []
        self._segment_id  = self._next_segment_id()
        self._file        = self._open_segment(self._segment_id)

    def _segment_path(self, seg_id: int) -> str:
        return os.path.join(self._dir, f"wal_{seg_id:06d}.log")

    def _next_segment_id(self) -> int:
        existing = self._list_segments()
        return existing[-1] + 1 if existing else 1

    def _list_segments(self) -> list[int]:
        ids = []
        for name in sorted(os.listdir(self._dir)):
            if name.startswith("wal_") and name.endswith(".log"):
                try:
                    ids.append(int(name[4:-4]))
                except ValueError:
                    continue
        return ids

    def _open_segment(self, seg_id: int) -> object:
        return open(self._segment_path(seg_id), "a", encoding="utf-8")

    def log(self, op: str, key: str, value: str | None = None,
            expiry: float | None = None) -> None:
        record = {
            "op_id":  next(self._counter),
            "ts":     time.time(),
            "op":     op,
            "key":    key,
            "value":  value,
            "expiry": expiry,
        }
        self._buffer.append(json.dumps(record) + "\n")
        self._write_count += 1
        if self._write_count % self._sync_every == 0:
            self._file.write("".join(self._buffer))
            self._buffer.clear()
            self._file.flush()
            os.fsync(self._file.fileno())

    def rotate(self) -> None:
        """Start a new segment. Call after a MemTable flush is durable on disk.

        Old segments are now redundant (their data is in SSTables) and get deleted.
        """
        self.sync()
        self._file.close()
        old_segments = self._list_segments()
        self._segment_id = (old_segments[-1] + 1) if old_segments else 1
        self._file = self._open_segment(self._segment_id)
        for seg_id in old_segments:
            if seg_id < self._segment_id:
                path = self._segment_path(seg_id)
                if os.path.exists(path):
                    os.remove(path)

    def replay(self, store) -> None:
        original_wal = store._wal
        store._wal = None
        try:
            seen: set[int] = set()
            for seg_id in self._list_segments():
                path = self._segment_path(seg_id)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for raw in f:
                            raw = raw.strip()
                            if not raw:
                                continue
                            try:
                                rec = json.loads(raw)
                            except json.JSONDecodeError:
                                continue
                            op_id = rec.get("op_id")
                            if op_id in seen:
                                continue
                            seen.add(op_id)
                            op  = rec.get("op")
                            key = rec.get("key")
                            if op == "SET":
                                expiry = rec.get("expiry")
                                if expiry and time.time() > expiry:
                                    continue
                                store.set(key, rec.get("value"), expiry=expiry)
                            elif op == "DELETE":
                                store.delete(key)
                except FileNotFoundError:
                    continue
        finally:
            store._wal = original_wal

    def sync(self) -> None:
        if self._buffer:
            self._file.write("".join(self._buffer))
            self._buffer.clear()
        self._file.flush()
        os.fsync(self._file.fileno())

    def close(self) -> None:
        self.sync()
        self._file.close()
