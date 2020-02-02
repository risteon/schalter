#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

"""


class ConfigScope:
    def __init__(self):
        self.parts = []

    @property
    def fullname(self):
        return "/".join(self.parts)

    def make_scope(self, name: str):
        self.parts.append(name)
        return self

    def release_scope(self):
        self.parts.pop()
