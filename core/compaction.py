from __future__ import annotations
import os
import time
import config


def compact(sst_paths: list[str], output_path: str) -> str:
    """
    Merge multiple SSTable files into one.
    Newest file wins on duplicate keys. Tombstones and expired keys are dropped.
    Returns the output path.
    """
    merged: dict[str, tuple[str, float]] = {}  # key -> (value, expiry)

    for path in sst_paths:
        with open(path, "rb") as f:
            for line in f:
                line = line.decode("utf-8").rstrip("\n")
                parts = line.split("\t")
                if len(parts) != 3:
                    continue
                key, value, expiry_str = parts
                merged[key] = (value, float(expiry_str))  # later file overwrites earlier

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    now = time.time()

    with open(output_path, "wb") as out:
        for key in sorted(merged):
            value, expiry = merged[key]
            if value == "__tombstone__":
                continue                    # drop deletes
            if expiry and now > expiry:
                continue                    # drop expired
            line = f"{key}\t{value}\t{expiry}\n"
            out.write(line.encode("utf-8"))

    for path in sst_paths:
        os.remove(path)

    return output_path
