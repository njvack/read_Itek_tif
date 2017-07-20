#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017 Board of Regents of the University of Wisconsin System
# Written by Nathan Vack <njvack@wisc.edu>

"""Usage: itf2csv [options] <data_file> [<output_file>]

Reads a .itf file written by ItekAnalyze, and converts it to a .csv format,
with one channel per row, followed by parallel port data. If a corresponding
.itf.ita file exists, it reads that as well and uses it to scale the data.

Made to mirror, as closely as possible, the behavor of docs/readitf.c

Options:
  -v, --verbose  Display debugging output
"""

import sys
import logging

from read_itek import __version__ as VERSION
from read_itek import reader
from read_itek.vendor.docopt import docopt

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def main(argv=None):
    args = docopt(__doc__, version="read_itek {}".format(VERSION), argv=argv)
    if args['--verbose']:
        logger.setLevel(logging.DEBUG)
        reader.logger.setLevel(logging.DEBUG)
    logger.debug(args)
    data, cards = reader.read_data(args['<data_file>'])
    outstream = sys.stdout
    if args['<output_file>']:
        outstream = open(args['<output_file>'], 'w')
    write_data(data, cards, outstream)


def write_data(data, cards, outstream):
    logger.debug(cards)
    for i, ch in enumerate(data['channels'].T):
        # This is incorrect! I'm leaving this here to emulate old behavior.
        # You really want reader.card_for_channel(cards, i)
        # but we don't ask for a channel_map here.
        card = cards[i // len(cards)]
        scale_factor = reader.scale_factor(card['gain'])
        scaled = ch * scale_factor
        outstream.write(",".join(str(v) for v in scaled) + "\n")
    outstream.write(",".join(str(v) for v in data['parallel_port']) + "\n")


if __name__ == '__main__':
    main()
