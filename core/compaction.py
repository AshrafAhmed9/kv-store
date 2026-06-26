from __future__ import annotations
import os
import time
import zlib


def compact(sst_paths: list[str], output_path: str) -> str:
    merged: dict[str, tuple[str, float]] = {}

    for path in sst_paths:
        with open(path, "rb") as f:
            for line in f:
                line = line.decode("utf-8").rstrip("\n")
                parts = line.split("\t")
                if len(parts) != 3:
                    continue
                key, value, expiry_str = parts
                merged[key] = (value, float(expiry_str))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    now = time.time()
    tmp = output_path + ".tmp"

    with open(tmp, "wb") as out:
        for key in sorted(merged):
            value, expiry = merged[key]
            if value == "__tombstone__":
                continue
            if expiry and now > expiry:
                continue
            line = f"{key}\t{value}\t{expiry}\n"
            out.write(line.encode("utf-8"))
        out.flush()
        os.fsync(out.fileno())

    os.replace(tmp, output_path)

    for path in sst_paths:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    return output_path
