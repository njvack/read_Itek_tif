#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017 Board of Regents of the University of Wisconsin System
# Written by Nathan Vack <njvack@wisc.edu>

"""Usage: itf2hdf5 [options] <itf_file> <hdf5_file>

Converts a .itf and .itf.ita file (if available) pair into a single HDF5 file.

Options:
  -v --verbose           Show debugging output
  --card_map=<order>     Change the mapping of cards to channel blocks
                         (16 numbers separated by commas)
                         [default: 1,0,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
  --all                  Capture channels, even if the corresponding card is
                         off
  --channel_names=<str>  Use a string of the format num1:name,num2:name,...
                         to name the channels.

The output file layout looks like:

/channels/channel_XXX:  The data for a channel. Signed 32-bit integer.
  scale_factor: The scale factor needed to convert this channel to mV.
  gain:         The gain, as read from the .ita file
  lpf:          The lowpass filter cutoff, as read from the .ita file
  on:           Whether the channel is on or not, as read from the .ita file

/channels/NAME:         An alias for one of the numbered channels.

/parallel_port:         Parallel port data. 1 unsigned byte / sample.

/is_missing:            True if this frame is missing (as determied by the
                        record counter and whether read frames are valid).
                        Boolean per sample.

/error_flags:           Error flags as reported by itekanalyze. (meaning?)
                        1 unsigned byte / sample.

/status_flags:          Status flags as reported by itekanalyze. (meaning?)
                        Unsigned byte / sample.

/tr_register:           I don't know what this is used for at all.
                        2 unsigned bytes / sample.

In addition, the root group has the following attributes:
  samples_per_second:   The sampling rate of the file. Always 1000 / 2.048.
  read_itek_version:    The version of read_itek that made this .hdf5 file.

If the .itf.ita file is missing, all channel attributes are set to 'unknown'
except for scale_factor, which is set to 1.0.
"""

import sys
import logging

import h5py

from read_itek import reader
from read_itek.vendor.docopt import docopt
from read_itek import __version__ as VERSION

logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def main():
    args = docopt(__doc__, version='read_itek {}'.format(VERSION))
    if args['--verbose']:
        logger.setLevel(logging.DEBUG)
        reader.logger.setLevel(logging.DEBUG)
    logger.debug(args)
    logger.debug('Reading {}'.format(args['<itf_file>']))

    data, cards = reader.read_data(args['<itf_file>'])
    channel_map = reader.channel_map(
        [int(v) for v in args['--card_map'].split(',')])
    channel_name_str = args.get('--channel_names', '')
    try:
        channel_names = channel_name_mapping(channel_name_str)
    except ValueError:
        logger.error("Didn't understand channel_names {}".format(
            channel_name_str))
        sys.exit(1)
    _save_data(
        args['<hdf5_file>'],
        data,
        cards,
        channel_map,
        args['--all'],
        channel_names)


def _save_data(
        outfile, data, cards, channel_map, save_all_channels, channel_names):
    logger.debug('Saving to {}'.format(outfile))
    h5f = h5py.File(outfile, 'w')
    h5f.attrs['samples_per_second'] = reader.SAMPLES_PER_SECOND
    h5f.attrs['read_itek_version'] = VERSION

    h5f.create_dataset(
        'parallel_port', data=data['parallel_port'], compression='gzip')
    h5f.create_dataset(
        'error_flags', data=data['error_flags'], compression='gzip')
    h5f.create_dataset(
        'status_flags', data=data['status_flags'], compression='gzip')
    h5f.create_dataset(
        'tr_register', data=data['tr_register'], compression='gzip')
    h5f.create_dataset(
        'is_missing', data=data['is_missing'], compression='gzip')

    _save_channels(
        h5f,
        data['channels'],
        cards,
        channel_map,
        save_all_channels,
        channel_names)
    h5f.close()


def get_card_data_with_fallback(cards, channel_number, channel_map):
    if cards is None:
        return {
            'gain': 'unknown',
            'scale_factor': 1,
            'on': 'unknown',
            'lpf': 'unknown'
        }

    c = cards[channel_map[channel_number]]
    return {
        'gain': c['gain'],
        'scale_factor': reader.scale_factor(c['gain']),
        'on': c['on'],
        'lpf': c['lpf']
    }


def channel_name_mapping(name_str):
    """
    Turns a string like '1:foo,2:bar' into the dict
    {1: 'foo', 2: 'bar'}
    May raise an exception if the string doens't follow this format.
    Returns {} for an empty string.
    """
    mapping_strs = str(name_str).split(',')
    str_pairs = [m.split(':') for m in mapping_strs]
    pairs = [
        [int(p[0]), p[1]] for p in str_pairs
        if len(p) == 2]
    return dict(pairs)


def _save_channels(
        h5f,
        channels,
        cards,
        channel_map,
        save_all_channels,
        channel_names):
    cg = h5f.create_group('/channels')
    for i, ch in enumerate(channels.T):
        card = get_card_data_with_fallback(cards, i, channel_map)
        if card['on'] or save_all_channels:
            channel_label = 'channel_{:03d}'.format(i)
            ds = cg.create_dataset(channel_label, data=ch, compression='gzip')
            for key, val in card.items():
                ds.attrs[key] = val
            channel_name = channel_names.get(i)
            if channel_name:
                logger.debug('Linking {} to {}'.format(
                    channel_name, channel_label))
                cg[channel_name] = ds


if __name__ == '__main__':
    main()
