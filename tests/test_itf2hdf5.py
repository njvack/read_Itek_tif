#!/usr/bin/env python
# -*- coding: utf-8 -*-

from os import path

import pytest

from read_itek import itf2hdf5
import logging
itf2hdf5.logger.setLevel(logging.DEBUG)

import h5py

DATA_PATH = path.join(path.dirname(path.abspath(__file__)), "data")


def test_shows_help():
    with pytest.raises(SystemExit):
        itf2hdf5.main()


def test_creates_file(tmpdir):
    infile = path.join(DATA_PATH, 'simple.itf')
    outfile = str(tmpdir.join("simple.hdf5"))
    itf2hdf5.main([infile, outfile])
    df = h5py.File(outfile, 'r')
    assert '/channels' in df
    assert len(df['/channels'].items()) == 8