#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_read_itek
----------------------------------

Tests for `reader` module.
"""

# import pytest


from read_itek import reader


def test_frame_size():
    assert reader.FRAME_DTYPE.itemsize == 400
