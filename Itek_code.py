# Here's what we need
import numpy as np



def is_good_frame(frame): #works
    # True if a frame is well-formed, false otherwise
    # record numbers, packet numbers, terminator should be 0x55 0xAA

    if (frame['recordNumber'] == frame['sameRecordNumber'] and
    frame['packet1'] == b'1' and frame['packet2'] == b'2' and
    frame['packet3'] == b'3' and frame['packet4'] == b'4' and
    frame['packet5'] == b'5' and frame['packet6'] == b'6' and
    frame['packet7'] == b'7' and frame['frameTerminator'][0] == 0x55 and
    frame['frameTerminator'][1] == 0xAA):
        return True
    else:
        return False

def seek_to_first_good_frame(frames): #works
    # Given an open file, seek() to the offset of the first well-formed frame in the file

    for i in range(frames.shape[0]):
        if is_good_frame(frames[i]) == True:
            first_good_index = i
            return first_good_index
    return None

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
