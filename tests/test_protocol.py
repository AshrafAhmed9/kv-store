from __future__ import annotations
import pytest
from kvstore.protocol import parse, ok, value, integer, error, multi_value


def test_parse_splits_command_and_args():
    cmd, args = parse("SET key value")
    assert cmd == "SET"
    assert args == ["key", "value"]

def test_parse_uppercases_command():
    cmd, _ = parse("get key")
    assert cmd == "GET"

def test_parse_empty_line_raises():
    with pytest.raises(ValueError):
        parse("   ")

def test_ok_and_error_markers():
    assert ok() == "+OK\r\n"
    assert error("bad") == "-ERR bad\r\n"

def test_value_and_integer_encoding():
    assert value("hi") == "+hi\r\n"
    assert value(None) == "$-1\r\n"
    assert integer(5) == ":5\r\n"

def test_multi_value_empty_and_nonempty():
    assert multi_value([]) == "$-1\r\n"
    assert multi_value([("a", "1"), ("b", "2")]) == "+a=1 b=2\r\n"
