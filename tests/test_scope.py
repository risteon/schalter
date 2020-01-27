# -*- coding: utf-8 -*-

__author__ = """Christoph Rist"""
__email__ = 'c.rist@posteo.de'

import pytest
from schalter import Schalter


def test_scope():
    Schalter.clear()

    @Schalter.scoped_configure
    def foo(*, a):
        return a

    with Schalter.Scope('A') as config_scope:
        foo(a=3)
        assert config_scope.fullname == 'A'

    with Schalter.Scope('B') as config_scope:
        foo(a=3)
        assert config_scope.fullname == 'B'


def test_scoped_function():
    Schalter.clear()

    @Schalter.scoped_configure
    def foo(*, a):
        return a

    @Schalter.Scope('A')
    def do_stuff_a():
        foo(a=3)

    @Schalter.Scope('B')
    def do_stuff_b():
        foo(a=3)
