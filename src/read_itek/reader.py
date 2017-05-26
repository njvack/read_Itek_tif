#!/usr/bin/env python

import numpy as np
import logging
logging.basicConfig(level=logging.DEBUG, format='%(message)s')
logger = logging.getLogger()

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
            return start_byte





def read_frames(infile): #works

    frame_dtype = np.dtype([

        ('packet1', 'c'), # This should be ASCII 1
        ('recordNumber', 'B'),
        ('errorFlags', 'B'),
        ('statusFlags', 'B'),
        ('parallelPort', 'B'),
        ('trRegister', '2B'),
        ('chans127to109', '(19,3)B'),

        ('packet2', 'c'), # This should be ASCII 2
        ('chans108to89', '(20,3)B'),

        ('packet3', 'c'), # This should be ASCII 3
        ('chans88to69', '(20,3)B'),

        ('packet4', 'c'), # This should be ASCII 4
        ('chans68to49', '(20,3)B'),

        ('packet5', 'c'), # This should be ASCII 5
        ('chans48to29', '(20,3)B'),

        ('packet6', 'c'), # This should be ASCII 6
        ('chans28to09', '(20,3)B'),

        ('packet7', 'c'), # This should be ASCII 7
        ('chans08to00', '(9,3)B'),

        ('sameRecordNumber', 'B'), # same record number
        ('frameTerminator', '(2,1)B') # end
    ])

    f = open(infile, 'rb')

    if f == None:
        print("The file is empty.")

    frames = np.fromfile(f, dtype = frame_dtype)

    return frames

def sign_extend(ar): #for big endian which means msb must be at index 0

    neg_mask = ar[:, 1] < 0

    for i in range(len(neg_mask)):
        if neg_mask[i] == True:
            ar[i, 0] = -1 #changing msb to show the value is negative
        else:
            ar[i, 0] = 0 #changing msb to show the value is positive

    return ar

def convert_three_byte(frame):
    data_out = np.zeros(128, dtype=np.int32)  # You're looking to make a 128-element array of int32.
    data_out.dtype = np.byte
    data_out = data_out.reshape(-1, 4)  # Shape is now (128,4) and dtype is byte

    # reverse the data in frame.
    # change 0:3 to 1:4 because data is big-endian
    data_out[0:9, 1:4] = frame['chans08to00'][::-1]
    data_out[9:29, 1:4] = frame['chans28to09'][::-1]
    data_out[29:49, 1:4] = frame['chans48to29'][::-1]
    data_out[49:69, 1:4] = frame['chans68to49'][::-1]
    data_out[69:89, 1:4] = frame['chans88to69'][::-1]
    data_out[89:109, 1:4] = frame['chans108to89'][::-1]
    data_out[109:128, 1:4] = frame['chans127to109'][::-1]

    data_out = sign_extend(data_out)

    data_out.dtype = np.int32

    data_out = data_out.flatten()

    return data_out


def make_frame_numbers(frames): #works
    # Given an open file seek()ed to the first good frame of data, return an increasing list of integers
    # indicating the index of each frame of data, starting at 0 and taking into account skipped frames

    number_array = np.zeros(frames.shape, dtype=np.intp)

    first_good_frame = seek_to_first_good_frame(frames)

    record_numbers = np.zeros(0)
    most_frames = np.zeros(0)
    running_sum = 0

    for i in range(first_good_frame, frames.shape[0]):
        record_numbers = np.append(record_numbers, frames[i]['recordNumber'])

    derivatives = np.diff(record_numbers)

    for i in range(derivatives.size):
        if derivatives[i] < 0:
            derivatives[i] = derivatives[i] + 256
        running_sum += derivatives[i]
        most_frames = np.append(most_frames, running_sum)

    # compute frame numbers, will be one element too short
    number_array[1:] = most_frames
    return number_array

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
