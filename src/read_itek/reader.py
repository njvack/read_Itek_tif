# -*- coding: utf-8 -*-
# Copyright (c) 2017 Board of Regents of the University of Wisconsin System
# Written by Nathan Vack <njvack@wisc.edu>

import numpy as np
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Note that the channel data is stored in 3-byte, big-endian, 2s compliment
# signed words. We'll need to convert them into 4-byte words for this to make
# any sense.

FRAME_DTYPE = np.dtype([
    ('packet1', 'c'),  # should be ASCII 1
    ('recordNumber', 'B'),
    ('errorFlags', 'B'),
    ('statusFlags', 'B'),
    ('parallelPort', 'B'),
    ('trRegister', '2B'),
    ('chans127to109', '(19,3)B'),
    ('packet2', 'c'),  # should be ASCII 2
    ('chans108to89', '(20,3)B'),
    ('packet3', 'c'),  # should be ASCII 3
    ('chans88to69', '(20,3)B'),
    ('packet4', 'c'),  # should be ASCII 4
    ('chans68to49', '(20,3)B'),
    ('packet5', 'c'),  # should be ASCII 5
    ('chans48to29', '(20,3)B'),
    ('packet6', 'c'),  # should be ASCII 6
    ('chans28to09', '(20,3)B'),
    ('packet7', 'c'),  # should be ASCII 7
    ('chans08to00', '(9,3)B'),
    ('sameRecordNumber', 'B'),  # Same as recordNumber
    ('frameTerminator', '2B')  # Should be [0x55 0xAA]
])

INTERNAL_DTYPE = np.dtype([
    ('error_flags', 'B'),
    ('status_flags', 'B'),
    ('parallel_port', 'B'),
    ('tr_register', '2B'),
    ('channels', '<i4', 128),
    ('is_missing', '?')
])

ITA_DTYPE = np.dtype([
    ('gain', 'd'),
    ('lpf', 'd'),
    ('on', '?')
])


CHANNELS = 128
CARDS = 16
CHANNELS_PER_CARD = CHANNELS // CARDS

GAIN_MAP = {
    '0': 400,
    '1': 10000,
    '2': 2000
}

FILTER_MAP = {
    '0': 100,
    '1': 300
}

ON_MAP = {
    'true': True,
    'false': False
}

ITA_MAPPER = {
    'on': ON_MAP,
    'lpf': FILTER_MAP,
    'gain': GAIN_MAP
}

V_REF = 2.5
BIT_RES = pow(2.0, 23.0) - 1.0
MICROV = 1.0e+06

SAMPLES_PER_SECOND = 1000 / 2.048


def read_data(itk_filename):
    logger.debug('Reading {}'.format(itk_filename))
    ita_filename = itk_filename + ".ita"
    frames = None
    cards = None
    with open(itk_filename, "rb") as f:
        frames = read_frames(f)
    itk_data = convert_frames_to_internal_type(frames)
    logger.debug("{} frames are missing.".format(
        np.sum(itk_data['is_missing'])))
    try:
        with open(ita_filename, "r") as f:
            cards = read_ita(f)
    except IOError:
        logger.warn("Could not read {}".format(ita_filename))
    return (itk_data, cards)


def open_file_size(infile):
    pos = infile.tell()
    infile.seek(0, 2)
    size = infile.tell()
    infile.seek(pos)
    return size


def read_frames(infile):
    total_bytes = open_file_size(infile)
    max_possible_frames = total_bytes // FRAME_DTYPE.itemsize
    frames = np.zeros(max_possible_frames, dtype=FRAME_DTYPE)
    logger.debug("File size is {0} bytes, allocated {1} frames".format(
        total_bytes, max_possible_frames))
    infile.seek(0)
    max_index = 0
    for frame_index, frame in enumerate(generate_valid_frames(infile)):
        frames[frame_index] = frame
        max_index = frame_index
    logger.debug("Read {0} valid frames.".format(max_index))
    return frames


def is_good_frame(frame):
    # True if a frame is well-formed, false otherwise
    # record numbers, packet numbers, terminator should be 0x55 0xAA
    return (
        frame['recordNumber'] == frame['sameRecordNumber'] and
        frame['packet1'] == b'1' and
        frame['packet2'] == b'2' and
        frame['packet3'] == b'3' and
        frame['packet4'] == b'4' and
        frame['packet5'] == b'5' and
        frame['packet6'] == b'6' and
        frame['packet7'] == b'7' and
        frame['frameTerminator'][0] == 0x55 and
        frame['frameTerminator'][1] == 0xAA
    )


def generate_valid_frames(infile):
    infile.seek(0)
    blank = np.zeros(1, dtype=FRAME_DTYPE)[0]
    frame = blank
    while not is_good_frame(frame):
        cur_byte = infile.tell()
        read = np.fromfile(infile, count=1, dtype=FRAME_DTYPE)
        if len(read) < 1:
            logger.debug("Reached end of file.")
            return
        frame = read[0]
        if not is_good_frame(frame):
            logger.debug("Read bad frame at byte {0}.".format(
                cur_byte, frame))
            infile.seek(cur_byte + 1)
        else:
            yield frame
        frame = blank


def convert_channels_to_le_i4(frames):
    int32_data = np.zeros((len(frames), CHANNELS), '<i4')
    int32_data.dtype = np.byte
    int32_data = int32_data.reshape(len(frames), CHANNELS, 4)
    # We're swapping both the order of the channel blocks and the order of the
    # bytes
    int32_data[:, 0:9, 1:4] = frames['chans08to00'][:, ::-1, ::-1]
    int32_data[:, 9:29, 1:4] = frames['chans28to09'][:, ::-1, ::-1]
    int32_data[:, 29:49, 1:4] = frames['chans48to29'][:, ::-1, ::-1]
    int32_data[:, 49:69, 1:4] = frames['chans68to49'][:, ::-1, ::-1]
    int32_data[:, 69:89, 1:4] = frames['chans88to69'][:, ::-1, ::-1]
    int32_data[:, 89:109, 1:4] = frames['chans108to89'][:, ::-1, ::-1]
    int32_data[:, 109:128, 1:4] = frames['chans127to109'][:, ::-1, ::-1]
    sign_mask = int32_data[:, :, 1] < 0
    int32_data[:, :, 0][sign_mask] = -1
    int32_data = int32_data.reshape(len(frames), CHANNELS * 4)
    int32_data.dtype = '<i4'
    return int32_data


def read_ita(infile):
    ita_data = np.zeros(CARDS, dtype=ITA_DTYPE)
    for line in infile:
        line = line.strip()
        cnum, key, val = parse_ita_line(line)
        ita_data[key][cnum] = map_ita_val(key, val)
    return ita_data


def parse_ita_line(line):
    full_key, val = line.split("=")
    _, card_num_str, key = full_key.split(".")
    cnum = int(card_num_str)
    return cnum, key, val


def map_ita_val(key, val):
    mapper = ITA_MAPPER[key]
    return mapper[val]


def scale_factor(gain):
    return (V_REF * MICROV) / (BIT_RES * gain)


def convert_frames_to_internal_type(frames):
    # Simplifies the frames structure, and converts its 3-byte ints into
    # int32.
    rnums = record_numbers(frames)
    internal_struct = np.zeros((rnums[-1] + 1), dtype=INTERNAL_DTYPE)
    internal_struct['is_missing'] = True
    internal_struct['is_missing'][rnums] = False
    internal_struct['channels'][rnums] = convert_channels_to_le_i4(frames)
    internal_struct['error_flags'][rnums] = frames['errorFlags']
    internal_struct['status_flags'][rnums] = frames['statusFlags']
    internal_struct['parallel_port'][rnums] = frames['parallelPort']
    internal_struct['tr_register'][rnums] = frames['trRegister']
    return internal_struct


def record_numbers(frames):
    record_counter = frames['recordNumber'].astype(np.int32)
    changes = np.diff(record_counter)

    # Since recordNumber is a ubyte, when we hit 255 we wrap back to 0 and the
    # derivative is -255. Adding 256 to this brings the numbers back around.
    # Note that this fails if we wind up skipping more than 255 frames in a row
    # but there's no way to detect that anyhow
    changes[changes < 0] += 256
    recnums = np.cumsum(changes)

    out = np.zeros(len(frames), dtype=np.int32)
    out[1:] = recnums
    return out


def channel_map(card_order):
    """
    Get a mapping between channels and cards -- there are 8 channels per
    card, and 16 channels in the system for a total of 128 channels.
    Normally, this would just be 0000000011111111...1515151515151515
    but in this case, channels 0-7 are on card 1, channels 8-15 are on card
    2
    Anyhow this returns CHANNELS integers such that channel_map[i] tells
    which card you're dealing with.
    """
    sorted_order = sorted(list(card_order))
    if not sorted_order == list(range(CARDS)):
        raise ValueError("channel_order must contain 0 through 15")
    card_ar = np.array(card_order)
    return np.repeat(card_ar, CHANNELS_PER_CARD)
