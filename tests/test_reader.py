#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path
from read_itek import reader
import logging
reader.logger.setLevel(logging.DEBUG)


DATA_PATH = path.join(path.dirname(path.abspath(__file__)), "data")


def test_frame_size():
    # Yes I know this is daft
    assert reader.FRAME_DTYPE.itemsize == 400


def test_reads_file():
    f = open(path.join(DATA_PATH, "simple.itf"), "r")
    frames = reader.read_frames(f)
    assert len(frames) > 0


def test_skips_broken_data():
    f = open(path.join(DATA_PATH, "padded.itf"), "r")
    frames = reader.read_frames(f)
    assert len(frames) > 0
