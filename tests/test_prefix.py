# -*- coding: utf-8 -*-

__author__ = """Christoph Rist"""
__email__ = "c.rist@posteo.de"

import pytest
from schalter import Schalter


def test_prefix():
    Schalter.clear()

    @Schalter.prefix("test")
    @Schalter.configure("a")
    def foo(*, a):
        return a

    Schalter["test/a"] = 3
    foo()
