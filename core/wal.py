from __future__ import annotations
import itertools
import json
import os
import time

class WAL:
    def __init__(self, path: str, sync_every: int = 1):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._path        = path
        self._sync_every  = sync_every
        self._write_count = 0
        self._counter     = itertools.count(1)
        self._buffer: list[str] = []
        self._file = open(path, "a", encoding="utf-8")

    def log(self, op: str, key: str, value: str | None = None, expiry: float | None = None) -> None:
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

    def replay(self, store) -> None:
        original_wal = store._wal
        store._wal = None
        try:
            seen: set[int] = set()
            with open(self._path, "r", encoding="utf-8") as f:
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
            pass
        finally:
            store._wal = original_wal

    def sync(self) -> None:
        if self._buffer:
            self._file.write("".join(self._buffer))
            self._buffer.clear()
        self._file.flush()

    def close(self) -> None:
        self.sync()
        self._file.close()
