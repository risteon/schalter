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


def test_prefix_useless_warning(caplog):
    @Schalter.prefix("useless")
    def bar():
        pass

    assert "WARNING" in caplog.text
    assert caplog.records
    caplog.clear()

    bar()
