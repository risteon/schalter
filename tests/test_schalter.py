# -*- coding: utf-8 -*-

__author__ = """Christoph Rist"""
__email__ = "c.rist@posteo.de"

import pytest
from schalter import Schalter


def test_schalter():
    Schalter.clear()

    @Schalter.configure
    def add_constant(x: int, *, constant_value: int = 1):
        return x + constant_value

    assert Schalter["constant_value"] == 1

    assert add_constant(1) == 2
    assert Schalter["constant_value"] == 1

    assert add_constant(1, constant_value=3) == 4
    assert Schalter["constant_value"] == 3

    Schalter["another_value"] = 42

    @Schalter.configure
    def check_value(expected, *, another_value: int = -1):
        assert expected == another_value

    check_value(42)
    check_value(1, another_value=1)
    check_value(1)


def test_empty_configures(caplog):
    Schalter.clear()

    # should issue a warning
    @Schalter.configure()
    def empty():
        pass

    assert "WARNING" in caplog.text
    assert caplog.records
    caplog.clear()

    @Schalter.configure()
    def empty(*_args):
        pass

    assert "WARNING" in caplog.text
    assert caplog.records
    caplog.clear()


def test_multiple_configures():
    Schalter.clear()

    @Schalter.configure("a")
    @Schalter.configure("b")
    def foo(*, a, b, c, d):
        return a, b, c, d

    with pytest.raises(KeyError):
        _aa, _bb, _cc, _dd = foo(c=3, d=4)

    Schalter["a"] = 1
    Schalter["b"] = 2

    aa, bb, cc, dd = foo(c=3, d=4)
    assert aa == 1 and bb == 2


def test_subset_configures_and_overrides():
    Schalter.clear()

    @Schalter.configure("a")
    def foo(*, a: int = 1, b: int = 2):
        return a * b

    assert Schalter["a"] == 1
    with pytest.raises(KeyError):
        _ = Schalter["b"]

    @Schalter.configure("b")
    def bar(*, a: int = 2, b: int = 3):
        return a * b

    assert Schalter["b"] == 3
    assert bar() == 6

    @Schalter.configure
    def baz(*, a, b):
        return a * b

    # Schalter decorator marks the kwonly args as 'with default' to make this call possible
    assert baz() == 3
    assert foo(b=3) == 3
    # default is overridden
    assert baz(a=7) == 21
    assert baz(b=4) == 28
    assert foo(b=3) == 21
    assert bar() == 8


def test_functions_callable():
    Schalter.clear()

    @Schalter.configure("x")
    def foo(*, x):
        pass

    # This raises a key error, because there is no value for x
    # instead of a TypeError for an unsupplied argument
    with pytest.raises(KeyError):
        foo()

    @Schalter.configure("a")
    def not_callable(*, c, a):
        pass

    # c is a kwonly arg that is not configured. May not be marked as default available.
    with pytest.raises(TypeError):
        not_callable()

    @Schalter.configure("a")
    @Schalter.configure("c")
    def is_callable(*, c, a):
        pass

    Schalter["a"] = 0
    Schalter["c"] = 0
    is_callable()


def test_remap_key():
    Schalter.clear()

    @Schalter.configure(local_name="config_name")
    def f(*, local_name: str = "default_value"):
        print(local_name)

    assert Schalter["config_name"] == "default_value"

    @Schalter.configure("foo", bar="baz")
    def x(*, foo: int = 3, bar: int = 5):
        _ = foo * bar

    assert Schalter["foo"] == 3
    assert Schalter["baz"] == 5
    with pytest.raises(KeyError):
        _ = Schalter["bar"]

    @Schalter.configure(foo="bar", bar="foo")
    def y_swap(*, foo, bar):
        return foo, bar

    assert y_swap(foo=42) == (42, 3)


def test_misc():
    Schalter.clear()

    # make sure that this does not configure the function arg 'a'
    # and does not contain a config value 'b'
    @Schalter.configure(b="a")
    def foo(*, a: int = 4, b: int):
        return a * b

    assert foo(b=5) == 20
    assert Schalter["a"] == 5
    assert not bool("b" in Schalter.get_config())
    assert "b" not in Schalter.get_config()
    assert not bool("b" in Schalter)
    with pytest.raises(KeyError):
        _ = Schalter["b"]

    Schalter["c"] = 0
    Schalter["d"] = 1

    @Schalter.configure(c="d", d="c")
    def bar(*, c: int = 4, d: int = 5):
        return c, d

    assert Schalter["c"] == 0
    assert Schalter["d"] == 1
    assert (1, 0) == bar()


def test_do_not_override_with_default_values():
    Schalter.clear()
    # A (later defined) default value does not override a manually supplied parameter.

    Schalter["constant"] = 4

    @Schalter.configure("constant")
    def foo(*, constant=-1):
        return constant

    assert foo() == 4


def test_multiple_default_values():
    Schalter.clear()

    with pytest.raises(ValueError):

        @Schalter.configure
        def add_constant_a(x: int, *, constant_value: int = 1):
            return x + constant_value

        @Schalter.configure
        def add_constant_b(x: int, *, constant_value: int = 2):
            return x + constant_value

    assert Schalter["constant_value"] == 1

    @Schalter.configure
    def add_constant_c(x: int, *, constant_value: int = 1):
        return x + constant_value

    Schalter.clear()

    @Schalter.configure
    def foo(*, _name: str = "baz"):
        pass

    @Schalter.configure
    def bar(*, _name: str = "baz"):
        pass

    with pytest.raises(ValueError):

        @Schalter.configure
        def foo(*, _name2: str = "baz"):
            pass

        @Schalter.configure
        def bar(*, _name2: str = "bar"):
            pass
