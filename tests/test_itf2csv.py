# Copyright (c) 2017 Board of Regents of the University of Wisconsin System
# Written by Nathan Vack <njvack@wisc.edu>


from os import path

import pytest

from read_itek import itf2csv
import logging
itf2csv.logger.setLevel(logging.DEBUG)

DATA_PATH = path.join(path.dirname(path.abspath(__file__)), "data")


def test_shows_help():
    with pytest.raises(SystemExit):
        itf2csv.main()


def test_basic_execute(capsys):
    infile = path.join(DATA_PATH, 'simple.itf')
    itf2csv.main([infile])
    out, err = capsys.readouterr()
    assert len(out.split("\n")) == 130
