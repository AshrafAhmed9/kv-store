"""Write-ahead log: every write is recorded here before it's considered done.

This is what makes crash recovery possible. If the process dies, the
MemTable (which lives only in RAM) is gone — but replaying the WAL on
restart reconstructs it exactly. Segmented into numbered files so old
segments can be deleted once their data is safely in an SSTable.
"""
from __future__ import annotations
import json
import os
import time


class WAL:
    def __init__(self, directory: str, sync_every: int = 1):
        os.makedirs(directory, exist_ok=True)
        self._dir = directory
        self._sync_every = sync_every
        self._writes_logged = 0   # doubles as the next op_id
        self._buffer: list[str] = []
        self._segment_id = self._next_segment_id()
        self._file = self._open_segment(self._segment_id)

    def log(self, op: str, key: str, value: str | None = None,
            expiry: float | None = None) -> None:
        """Buffer one write. Only every Nth call actually touches disk (see sync_every) —
        that's the batching that trades a little durability window for a lot of throughput."""
        self._writes_logged += 1
        record = {
            "op_id": self._writes_logged,
            "op": op,
            "key": key,
            "value": value,
            "expiry": expiry,
        }
        self._buffer.append(json.dumps(record) + "\n")
        if self._writes_logged % self._sync_every == 0:
            self.sync()

    def sync(self) -> None:
        """Force buffered writes to physical disk. flush() alone only reaches the
        OS page cache — fsync() is what survives a power loss."""
        if self._buffer:
            self._file.write("".join(self._buffer))
            self._buffer.clear()
        self._file.flush()
        os.fsync(self._file.fileno())

    def rotate(self) -> None:
        """Start a fresh segment and delete every older one.

        Only call this right after a MemTable flush is durably on disk — at that
        point the old segments' data lives in an SSTable, so they're redundant.
        """
        self.sync()
        self._file.close()
        old_segments = self._list_segments()
        self._segment_id = self._next_segment_id()
        self._file = self._open_segment(self._segment_id)
        for seg_id in old_segments:
            os.remove(self._segment_path(seg_id))

    def replay(self, store) -> None:
        """Re-apply every logged write to a freshly opened store. Used once, at startup."""
        original_wal = store._wal
        store._wal = None  # don't re-log writes we're replaying from the log
        try:
            seen_op_ids: set[int] = set()
            for seg_id in self._list_segments():
                self._replay_segment(seg_id, store, seen_op_ids)
        finally:
            store._wal = original_wal

    def _replay_segment(self, seg_id: int, store, seen_op_ids: set[int]) -> None:
        path = self._segment_path(seg_id)
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                record = self._parse_record(raw)
                if record is None or record["op_id"] in seen_op_ids:
                    continue  # skip a torn write, or a record already replayed once
                seen_op_ids.add(record["op_id"])
                self._apply(record, store)

    @staticmethod
    def _parse_record(raw: str) -> dict | None:
        raw = raw.strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None  # a partial line from a crash mid-write — safe to drop

    @staticmethod
    def _apply(record: dict, store) -> None:
        key = record.get("key")
        if record.get("op") == "SET":
            expiry = record.get("expiry")
            if expiry and time.time() > expiry:
                return
            store.set(key, record.get("value"), expiry=expiry)
        elif record.get("op") == "DELETE":
            store.delete(key)

    def close(self) -> None:
        self.sync()
        self._file.close()

    def _segment_path(self, seg_id: int) -> str:
        return os.path.join(self._dir, f"wal_{seg_id:06d}.log")

    def _next_segment_id(self) -> int:
        existing = self._list_segments()
        return existing[-1] + 1 if existing else 1

    def _list_segments(self) -> list[int]:
        ids = []
        for name in sorted(os.listdir(self._dir)):
            if name.startswith("wal_") and name.endswith(".log"):
                ids.append(int(name[4:-4]))
        return ids

    def _open_segment(self, seg_id: int):
        return open(self._segment_path(seg_id), "a", encoding="utf-8")
