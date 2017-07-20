#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path

import pytest

from read_itek import itf_clip_stats
import logging
itf_clip_stats.logger.setLevel(logging.DEBUG)

DATA_PATH = path.join(path.dirname(path.abspath(__file__)), "data")


def test_shows_help(capsys):
    with pytest.raises(SystemExit):
        itf_clip_stats.main()


def test_no_crash_on_read_file(capsys):
    itf_clip_stats.main([path.join(DATA_PATH, 'simple.itf')])
    out, err = capsys.readouterr()
    assert 'filename' in out
