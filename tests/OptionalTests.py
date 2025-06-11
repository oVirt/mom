import sys
import pytest
from mom.optional import Optional

def test_missing():
    assert Optional.missing().present is False

def test_missing_none():
    assert Optional.missing().orNone() is None

def test_missing_else():
    assert Optional.missing().orElse(False) is False

def test_missing_raise():
    with pytest.raises(RuntimeError):
        Optional.missing().orRaise(RuntimeError, "error")

def test_missing_map():
    assert Optional.missing().map(lambda val: 5/0).present is False

def test_missing_get():
    assert Optional.missing().get("key").present is False

def test_missing_item():
    assert Optional.missing()["key"].present is False

def test_missing_iter():
    with pytest.raises(StopIteration):
        next(iter(Optional.missing()))

def test_value():
    assert Optional("val").present is True
    assert Optional("val").value == "val"

def test_raise():
    assert Optional("val").orRaise(RuntimeError, "error") == "val"

def test_map():
    assert Optional("val").map(str.upper).value == "VAL"

def test_get():
    assert Optional({"key":"val"}).get("key").value == "val"

def test_get_default():
    assert Optional({"key": "val"}).get("key2", "default").value == "default"

def test_item():
    assert Optional({"key": "val"})["key"].value == "val"

def test_get_default_item():
    assert Optional({"key": "val"})["key2"].present is False

def test_iter():
    assert next(iter(Optional(["val"]))) == "val"
