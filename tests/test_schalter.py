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


def test_empty_configures(caplog):
    Schalter.clear()

    # should issue a warning
    @Schalter.configure()
    def empty():
        pass
    assert 'WARNING' in caplog.text
    assert caplog.records
    caplog.clear()

    @Schalter.configure()
    def empty(*_args):
        pass
    assert 'WARNING' in caplog.text
    assert caplog.records
    caplog.clear()


def test_subset_configures_and_overrides():
    Schalter.clear()

    @Schalter.configure('a')
    def foo(*, a: int = 1, b: int = 2):
        return a * b
    assert Schalter['a'] == 1
    with pytest.raises(KeyError):
        _ = Schalter['b']

    @Schalter.configure('b')
    def bar(*, a: int = 2, b: int = 3):
        return a * b
    assert Schalter['b'] == 3
    assert bar() == 6

    @Schalter.configure
    def baz(*, a, b):
        return a * b

    assert baz() == 3
    assert foo(b=3) == 3
    # default is overriden
    assert baz(a=7) == 21
    assert baz(b=4) == 28
    assert foo(b=3) == 21
    assert bar() == 8


def test_remap_key():
    Schalter.clear()

    @Schalter.configure('foo', bar='baz')
    def x(*, foo: int = 3, bar: int = 5):
        _ = foo * bar

    assert Schalter['foo'] == 3
    assert Schalter['baz'] == 5
    with pytest.raises(KeyError):
        _ = Schalter['bar']


def test_misc():
    Schalter.clear()

    @Schalter.configure(b='a')
    def foo(*, a: int = 4, b: int):
        return a * b
    assert foo() == 16


def test_multiple_default_values():
    Schalter.clear()

    with pytest.raises(ValueError):
        @Schalter.configure
        def add_constant_a(x: int, *, constant_value: int = 1):
            return x + constant_value

        @Schalter.configure
        def add_constant_b(x: int, *, constant_value: int = 2):
            return x + constant_value

    assert Schalter['constant_value'] == 1

    @Schalter.configure
    def add_constant_c(x: int, *, constant_value: int = 1):
        return x + constant_value
