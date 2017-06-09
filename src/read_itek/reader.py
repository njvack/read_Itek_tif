#!/usr/bin/env python

import numpy as np
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()

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
    ('record_number', 'B'),
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


def read_frames(infile):
    _seek_to_first_good_frame(infile)
    frames = np.fromfile(infile, dtype=FRAME_DTYPE)  # TODO: Handle truncation
    logger.debug("read {0} frames".format(len(frames)))
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


def first_good_frame_byte(infile):
    # Returns the byte offset of the first good frame in infile.
    # Does not change the byte position of infile.
    original_offset = infile.tell()
    first_good_frame_byte = None
    try:
        first_good_frame_byte = _seek_to_first_good_frame(infile)
    finally:
        infile.seek(original_offset)
    return first_good_frame_byte


def _seek_to_first_good_frame(infile):
    # Seeks to the first good frame in a infile, returns it. If we can't find
    # one, we'll read past the end of the file and throw an exception.
    # Leaves the position of infile altered.
    infile.seek(0, 2)
    file_length = infile.tell()
    logging.debug("file is {0} bytes long".format(file_length))
    for start_byte in range(file_length):
        logging.debug("looking for good frame at byte {0}".format(start_byte))
        infile.seek(start_byte)
        frame = np.fromfile(infile, count=1, dtype=FRAME_DTYPE)
        if is_good_frame(frame[0]):
            logger.debug("found good frame at byte {0}".format(start_byte))
            return start_byte


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


def convert_frames_to_internal_type(frames):
    # Simplifies the frames structure, and converts its 3-byte ints into
    # int32.
    rnums = record_numbers(frames)
    internal_struct = np.zeros((rnums[-1] + 1), dtype=INTERNAL_DTYPE)
    internal_struct['is_missing'] = True
    internal_struct['is_missing'][rnums] = False
    internal_struct['channels'][rnums] = convert_channels_to_le_i4(frames)
    internal_struct['record_number'][rnums] = record_numbers(frames)
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


def print_packet_line(frame_ar, packet):

    if (packet == 1):
        print("\tPacket", packet,"ID: '{0}', Record #: {1}. Error flags: {2}. Status flags: {3},".format(
                frame_ar['packet1'], frame_ar['recordNumber'], frame_ar['errorFlags'],
                frame_ar['statusFlags']))
        print ("\tParallel port: {0}, TR: {1}".format(frame_ar['parallelPort'],
                frame_ar['trRegister']))
    else:
        print ("\tPacket", packet,"ID: '{0}',".format(packet),)

def print_Chans(main_data, Chan_counter, Chan_dif_lim):

    Chan_dif = 0
    while (Chan_dif <= Chan_dif_lim):
        print ("Chan {0}: {1}".format(Chan_counter, main_data[Chan_counter]))
        if (Chan_dif == (Chan_dif_lim - 1)):
            print (",")
        Chan_counter = Chan_counter - 1
        Chan_dif = Chan_dif + 1

def make_human_readable(frames_ar, frame_nums):
    for i in range(frames_ar.shape[0]):
        print ("Data Frame: {0}".format(frame_nums[i]))
        main_data = convert_three_byte(frames_ar[i])
        Chan_counter = 127
        for packets in range(1, 8):
            if (packets == 7):
                print_packet_line(frames_ar[i], packets)
                print_Chans(main_data, Chan_counter, 19)
                print ("Record chk: {0},  Frame end: {1}.".format(frames_ar[i]['sameRecordNumber'],
                        frames_ar[i]['frameTerminator']))
            else:
                print_packet_line(frames_ar, packets)
                print_Chans(main_data, Chan_counter, 8)


def main():
    if (len(sys.argv) < 2):
        print (' General Info \n usage:", sys.argv[0],"<datafile.itf> [<outputfile.csv>]' +
        		'<datafile.itf> should be a file produced by'+
        		'the ItekAnalyse EMG data collection app.' +
        		'If a corresponding .itf.ita file is present,' +
        		'output values will be in mV, otherwise they' +
        		'will be in raw A-D converter 24-bit integers.' +
        		'<outputfile.csv> will be a comma-separated' +
        		'value text file of the input data.' +
        		'If <outputfile.csv> is not specified, the' +
        		'raw Itek data frames will be dumped to stdout' +
        		'in human-readable format.' +
        		'Build version: {0}. {1}'.format(2.01, time.ctime(os.path.getmtime(__file__))))
        sys.exit(1)

    infile = sys.argv[1]

    if (len(sys.argv) == 2):
        frames = read_frames(infile)
        array_frame_nums = make_frame_numbers(frames)
        make_human_readable(frames, array_frame_nums)
        sys.exit(0)

    outfile = sys.argv[2]

if __name__ == '__main__':
    main()
