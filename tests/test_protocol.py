from __future__ import annotations
import pytest
from kvstore.protocol import parse, ok, value, integer, error, multi_value
from kvstore.server import _dispatch, _COMMANDS


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


def test_unknown_command_reports_unknown():
    assert "unknown command" in _dispatch(None, "NOPE", [])


def test_internal_error_is_not_reported_as_unknown_command(monkeypatch):
    """A KeyError raised *inside* a handler must not be mistaken for an
    unrecognised command — they are different failures and hide different bugs."""
    def raises_key_error(store, args):
        raise KeyError("an internal lookup missed")

    monkeypatch.setitem(_COMMANDS, "BOOM", raises_key_error)
    reply = _dispatch(None, "BOOM", [])
    assert "unknown command" not in reply
    assert reply.startswith("-ERR")
