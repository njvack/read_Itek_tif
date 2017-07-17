#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017 Board of Regents of the University of Wisconsin System
# Written by Nathan Vack <njvack@wisc.edu>

"""Usage: itf_clip_stats [options] <itf_file>...

For each channel in each file, show how much of the channel is clipping. Prints
tab-separated output, of the format:

FILENAME    CHANNEL     PERCENT_CLIPPED

Options:
  -v --verbose           Show debugging output
  --channels=<chans>     A comma-separated list of channel numbers to report
                         or, 'on', or 'all'
                         [default: on]
  --channel_names=<str>  Use a string of the format num1:name,num2:name,...
                         to name the channels.
  --card_map=<order>     Change the mapping of cards to channel blocks.
                         (16 numbers separated by commas)
                         [default: 1,0,2,3,4,5,6,7,8,9,10,11,12,13,14,15]

"""

import sys
import csv
import logging

from read_itek import __version__ as VERSION
from read_itek import reader
from read_itek.vendor.docopt import docopt

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def main():
    args = docopt(__doc__, version="read_itek {}".format(VERSION))
    if args['--verbose']:
        logger.setLevel(logging.DEBUG)
        reader.logger.setLevel(logging.DEBUG)
    logger.debug(args)


def report_clip_stats(files):
    pass


if __name__ == '__main__':
    main()
