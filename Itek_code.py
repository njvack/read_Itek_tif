import numpy as np
import numpy.ma as ma

#total_frame = np.dtype([
#    ('data','(1,400)B')
#])

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

def checkPacketNums(frame_dtype, printCount):
    good_frames = []
    for i in range(frame_dtype.shape[0]):

        if frame_dtype[i][0] == b'1' and printCount <= 10:
            print("Packet number one of a frame is not in the correct location")
            printCount += 1

        if frame_dtype[i][7] == b'2' and printCount <= 10:
            print("Packet number two of a frame is not in the correct location")
            printCount += 1

        if frame_dtype[i][9] == b'3' and printCount <= 10:
            print("Packet number three of a frame is not in the correct location")
            printCount += 1

        if frame_dtype[i][11] == b'4' and printCount <= 10:
            print("Packet number four of a frame is not in the correct location")
            printCount += 1

        if frame_dtype[i][13] == b'5' and printCount <= 10:
            print("Packet number five of a frame is not in the correct location")
            printCount += 1

        if frame_dtype[i][15] == b'6' and printCount <= 10:
            print("Packet number six of a frame is not in the correct location")
            printCount += 1

        if frame_dtype[i][17] == b'7' and printCount <= 10:
            print("Packet number seven of a frame is not in the correct location")
            printCount += 1

        if printCount == 10:
            print("The print out statements for checking packet number has hit the limit.")

        if (frame_dtype[i][0] == b'1' and frame_dtype[i][7] == b'2' and
        frame_dtype[i][9] == b'3' and frame_dtype[i][11] == b'4' and
        frame_dtype[i][13] == b'5' and frame_dtype[i][15] == b'6' and
        frame_dtype[i][17] == b'7'):
            good_frames.insert(len(good_frames), i)
    return good_frames;

def checkRecNums(frame_dtype):
    error = False #to only print the error once not many times
    for i in range(frame_dtype.shape[0]):
        if (frame_dtype[0][19] == frame_dtype[0][1]):
            good_frames.insert(len(good_frames), i)
        if error == False:
            print("The frame is the incorrect size.")
            error = True
    return good_frames;


def badDataCheck(frame_dtype, badValCount):
    badValCount = 0
    isGood = True
    for i in range(frame_dtype.shape[0]):
        for j in range(6,12):
            if np.all(frame_dtype[i][j] == 255):
                badValCount += 1

            #includes first four chansxtoy arrays of data and marks data as bad
            #if all values are 255
            if badValCount >= 3:
                badValCount = 0  #reset count for next frame
                isGood = False
                break
        if isGood == True:
            good_frames.insert(len(good_frames), i)

    print(good_frames)
    return good_frames;

#used to store good frames from checking functions that will be compared
# Just a test commit comment
good_frames1 = []
good_frames2 = []
good_frames3 = []

final_frame = [] #used to store similar values from each of the compared lists

f = open('MRI 02-14-2017 11-54-17.itf', 'rb')

if f == None:
    print('This is an empty file.')

frames = np.fromfile(f, dtype = frame_dtype)

badValCount = 0 #used for imputing a zero as a parameter to count in a function that requires counting
good_frames1 = badDataCheck(frame_dtype, badValCount)
#good_frames2 = checkRecNums(frame_dtype)
#good_frames3 = checkPacketNums(frame_dtype, zeroValue)

#final_frame = set(good_frames1) & set(good_frames2) & set(good_frames3)

#print(good_frames1)
