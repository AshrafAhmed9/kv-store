from __future__ import annotations

def parse(line: str) -> tuple[str, list[str]]:
    parts = line.strip().split()
    if not parts:
        raise ValueError("empty command")
    return parts[0].upper(), parts[1:]


def ok() -> str:
    return "+OK\r\n"

def value(v: str | None) -> str:
    return f"+{v}\r\n" if v is not None else "$-1\r\n"

def integer(n: int) -> str:
    return f":{n}\r\n"

def error(msg: str) -> str:
    return f"-ERR {msg}\r\n"

def multi_value(pairs: list[tuple[str, str]]) -> str:
    if not pairs:
        return "$-1\r\n"
    lines = [f"{k}={v}" for k, v in pairs]
    return "+" + " ".join(lines) + "\r\n"
