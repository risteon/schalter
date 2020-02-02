# -*- coding: utf-8 -*-

__author__ = """Christoph Rist"""
__email__ = "c.rist@posteo.de"

import pytest
from schalter import Schalter


@pytest.fixture
def schalter_object_cleared():
    Schalter.clear()
    return Schalter


def test_default_config(schalter_object_cleared):
    d = schalter_object_cleared.get_config()
    assert len(d.config) == 0
