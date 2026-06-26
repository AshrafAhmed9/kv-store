import os
from core.durability import atomic_write


def test_atomic_write_creates_file(tmp_path):
    target = str(tmp_path / "x.dat")
    atomic_write(target, b"hello")
    with open(target, "rb") as f:
        assert f.read() == b"hello"


def test_atomic_write_leaves_no_tmp(tmp_path):
    target = str(tmp_path / "x.dat")
    atomic_write(target, b"hello")
    assert not os.path.exists(target + ".tmp")   # tmp was renamed away


def test_atomic_write_overwrites(tmp_path):
    target = str(tmp_path / "x.dat")
    atomic_write(target, b"old")
    atomic_write(target, b"new")
    with open(target, "rb") as f:
        assert f.read() == b"new"
