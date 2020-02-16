# -*- coding: utf-8 -*-

__author__ = """Christoph Rist"""
__email__ = "c.rist@posteo.de"

import pytest
from schalter import Schalter


def test_prefix_standard():
    Schalter.clear()

    @Schalter.prefix("test")
    @Schalter.configure("a")
    def foo(*, a):
        return a

    Schalter["test/a"] = 3
    foo()

    @Schalter.prefix("b")
    @Schalter.configure
    def bar(*, b: int, c: str):
        return b, c

    Schalter["b/b"] = 2
    Schalter["b/c"] = "baz"
    assert bar() == (2, "baz")

    @Schalter.configure("non_prefixed")
    @Schalter.prefix("some_prefix")
    @Schalter.configure("prefixed")
    def baz(*, prefixed, non_prefixed):
        return prefixed, non_prefixed

    Schalter["some_prefix/prefixed"] = 123
    Schalter["non_prefixed"] = 456
    assert baz() == (123, 456)

    with pytest.raises(KeyError):
        _ = Schalter["prefixed"]
    with pytest.raises(KeyError):
        _ = Schalter["some_prefix/non_prefixed"]


def test_multiple_prefixes():
    Schalter.clear()

    Schalter["first/second/leaf_a"] = 8
    Schalter["first/second/leaf_b"] = "foo"

    @Schalter.prefix("first")
    @Schalter.prefix("second")
    @Schalter.configure
    def foo(_unused, *, leaf_a, leaf_b):
        return _unused, leaf_a, leaf_b

    with pytest.raises(TypeError):
        _ = foo()

    assert foo(None) == (None, 8, "foo")


def test_multiple_prefixed_configures():
    Schalter.clear()

    Schalter["p/leaf_a"] = 8
    Schalter["p/leaf_b"] = "foo"

    @Schalter.prefix("p")
    @Schalter.configure("leaf_a")
    @Schalter.configure("leaf_b")
    def foo(_unused, *, leaf_a, leaf_b):
        return _unused, leaf_a, leaf_b

    with pytest.raises(TypeError):
        _ = foo()

    assert foo(None) == (None, 8, "foo")


def test_prefix_useless_warning(caplog):
    @Schalter.prefix("useless")
    def bar():
        pass

    assert "WARNING" in caplog.text
    assert caplog.records
    caplog.clear()

    bar()
