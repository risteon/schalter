# -*- coding: utf-8 -*-

__author__ = """Christoph Rist"""
__email__ = 'c.rist@posteo.de'

import pytest
from schalter import Schalter


def test_schalter():
    Schalter.clear()

    @Schalter.configure
    def add_constant(x: int, *, constant_value: int = 1):
        return x + constant_value

    assert Schalter['constant_value'] == 1

    assert add_constant(1) == 2
    assert Schalter['constant_value'] == 1

    assert add_constant(1, constant_value=3) == 4
    assert Schalter['constant_value'] == 3
