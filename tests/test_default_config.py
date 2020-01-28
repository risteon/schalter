# -*- coding: utf-8 -*-

__author__ = """Christoph Rist"""
__email__ = 'c.rist@posteo.de'

import pytest
from schalter import Schalter


def test_default_config():
    Schalter.clear()
    d = Schalter.get_config()
    assert type(d) == Schalter
    assert len(d.config) == 0

    @Schalter.configure()
    def foo(*, a):
        pass

    foo(a=3)
    assert Schalter['a'] == 3
