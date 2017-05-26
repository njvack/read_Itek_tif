/* READITF.H
 *
 * Header file for READITF.C.
 *
 * Copyright 2016 Board of Regents of the University of Wisconsin System
 *
 * Version history:
 * 2016-02-15	John Koger	Initial version.
 */

#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <math.h>
#include <string.h>


/* Each Itek amp channel has a gain setting of 400x, 2000x, or 10000x.
 * These are represented by config bits of 00, 01, 10, or 11.
 *
 * These gain settings can be set per-channel in the ItekAnalyse app,
 * but actually are applied card-wide (to all 8 channels on the same card).
 */
#define GAIN_400	0
#define GAIN_10000	1
#define GAIN_2000	2
#define GAIN_UNDEFINED	3

/* The Itek amps use TI ADS1278 A-D converters, which have an analog
 * input range of -Vref to +Vref, where Vref = 2.5 V. They output a
 * 24 bit 2's complement signed integer with values from 0x7FFFFF
 * (max, equivalent to +Vref input) down to 0xFFFFF (min, equivalent
 * to -Vref input), or from 2^23 - 1 max down to -2^23 -1 min.
 *
 * The signals will be in Volts, but we want to look at them in microVolts
 * so they need to be scaled up appropriately.
 *
 * And finally the signals will have been amplified by the gain values
 * of the amps, so they must be scaled down by the gain to reflect that.
 */
#define V_REF	2.5
#define BIT_RES pow(2.0, 23.0) - 1.0
#define MICROV	1.0e+06

/* Each Itek amp channel (or, really, card) also has a Low Pass Filter
 * setting of 100Hz or 300Hz, represented by a single bitflag.
 */
#define LPF_100Hz	0
#define LPF_300Hz	1

/* Each Itek amp has 1 - 16 hardware cards in it, and each card
 * has 8 data collection channels, for a total of up to 128 channels.
 * The ItekAnalyse data collection software is hard-coded to return
 * data for all 128 possible channels regardless of how many cards
 * are actually installed in the amps.
 */

#define ITEK_MAX_CARDS	16
#define ITEK_MAX_CHANS	128

struct itekChannel
{
	float		gain;
	float		*data;
	long		hardwareChannelNumber,
				numSamples;
};

/* Overall, data is sent from the Itek amps in the form of 400-byte
 * long data frames, consisting of 7 unequal-length packets. Each packet
 * is started by the ASCII character numeral of the packet, e.g. the
 * first packet starts with the char '1'. The data frame is concluded with
 * 0x55 0xAA. Data frames are sent from the amps once per every 2.048
 * milliseconds. It is the responsibility of the recording app (ItekAnalyse)
 * to capture every data frame, as the amps have no buffering or re-send
 * capabilities. Capture the data frames or lose them, more will keep coming.
 *
 * The first packet in a data frame starts with the character '1', then status
 * information (record number, error flags, status flags, parallel port
 * value, and transmit register), and then the raw data sample values for 
 * channels 127 (highest channel) through 109. The first packet is 61 bytes
 * long.
 *
 * The second packet starts with '2' then data for the channels 108 - 89.
 * It is 64 bytes long.
 *
 * Similarly, packets 3 - 6 start with '3' - '6' followed by the data
 * for channels 88 - 69 (packet 3) through channels 28 through 09 (packet 6).
 * Each of these packets is also 64 bytes long.
 *
 * Packet 7 starts with '7', then has the data for channels 08 - 00 (the
 * first channel), followed by a repeat of the record number, and
 * finally the data frame terminator bytes 0x55 0xAA.
 *
 * A .ITF file created by ItekAnalyse will contain a (large) number of
 * data frames. It is possible that garbage (partial frames?) can precede
 * the good data frames at the start of the file or follow them at the end
 * of the file.
 */

/* The following structs define the various parts of an Itek amp data frame.
 */

/* Itek amp channel data is sent in the form of 3 bytes per value,
 * aka big-endian 24-bit signed 2s-complement integers.
 */
struct threeByteInt
{
	unsigned char	msb,
			middle,
			lsb;
} __attribute__((packed));


/* Error flags are sent as 1 byte with only 1 bit used to indicate
 * buffer overflow. The other 7 bits are unused.
 */
struct errorFlags
{
	unsigned int	bufferOverflow:1,
			unusedBits:7;
} __attribute__((packed));


/* Status flags regarding the overall amps. Not sure what exactly
 * these mean yet.
 */
struct statusFlags
{
	unsigned int	PRKLSB:1,
			PRKMSB:1,
			PFOSD:1,
			BRKLSB:1,
			BRKMSB:1,
			BFOSD:1,
			unusedBits:2;
} __attribute__((packed));


/* Transmit register. This might indicate USB transmit speed? Not sure.
 */
struct trRegister
{
	unsigned char	msb,
			lsb;
} __attribute__((packed));


/* A complete Itek amp data frame. 400 bytes overall.
 */

struct itekDataFrame
{
	char		packet1;	/* Should be ASCII '1' char */
	unsigned char	recordNumber;
	struct errorFlags
			errorFlags;
	struct statusFlags
			statusFlags;
	unsigned char	parallelPortPins;
	struct trRegister
			tr;

	struct threeByteInt
			chans127to109[19];

	char		packet2;	/* Should be ASCII '2' char */
	struct threeByteInt
			chans108to89[20];

	char		packet3;	/* Should be ASCII '3' char */
	struct threeByteInt
			chans88to69[20];

	char		packet4;	/* Should be ASCII '4' char */
	struct threeByteInt
			chans68to49[20];

	char		packet5;	/* Should be ASCII '5' char */
	struct threeByteInt
			chans48to29[20];
			
	char		packet6;	/* Should be ASCII '6' char */
	struct threeByteInt
			chans28to09[20];
			
	char		packet7;	/* Should be ASCII '7' char */
	struct threeByteInt
			chans08to00[9];

	unsigned char	recordNumberCheck;

	unsigned char	frameTerminator[2];	/* Should be 0x55 0xAA */
} __attribute__((packed));


/* This union can be handy for poking around in a data frame byte by byte
 * (for example if there seems to be garbage in the middle of a .ITF file
 * and a good data frame start needs to be located).
 */
union itekDataUnion
{
	/* sizeof(itekDataUnion) and sizeof(itekDataFrame) should be 400 */
	struct itekDataFrame
			dataFrame;
	unsigned char	u[400];
} __attribute__((packed));


/* In addition to the data frames that ItekAnalyse stores in the .ITF
 * files, it also stores amplifier card info in a human-readable
 * text .ITF.ITA file. The info includes whether each specific card
 * (out of 16 possible) is on or off at the time of recording, and
 * what each card's gain and low-pass filter settings are. There is
 * one line in the .ITF.ITA file for each setting for each card.
 */
struct itekCardInfo
{
	int	onOff,			/* 0 = off, 1 = on */
		rawLowPassFilter,	/* 0 = 100Hz, 1 = 300Hz */
		rawGain;		/* 0 = 400, 1 = 10K, 2 = 2K */
	float	lowPassFilter,		/* 100.0 Hz or 300.0 Hz */
		gain;			/* 400.0, 2000.0, or 10000.0 */
};


/* Check to see if a data frame has the packet-start chars '1' - '7'
 * in the expected places. Return 1 if things look good, 0 if they don't.
 */
int checkItekDataFrame(struct itekDataFrame *df);


/* Read in all of the data frames in a .ITF file. If data frames
 * are successfully read, return a pointer to a malloc'ed array of
 * data frames, or NULL if the file read failed. Set the long pointed
 * to by *numSamples to the number of data frames read in. *numSamples
 * equates to the number of samples per data channel read in.
 */
struct itekDataFrame * readItekData(char *fileName, long *numSamples);


/* Convert a 24-bit big-endian 2's-complement signed integer to a
 * regular integer and then to a float.
 */
float itekFloat(struct threeByteInt *itekValue);


/* Given a data frame, extract the data from the frame for
 * a given channel, 0 - 127.
 */
float itekHardwareChannelData(int chanNum, struct itekDataFrame *df);


/* Given a data frame, dump its contents to stdout in a human-readable
 * format.
 */
void dumpItekDataFrame(struct itekDataFrame *df);


/* Given an array of data frames, dump their contents to stdout in a
 * human-readable format.
 */
void dumpItekDataFrames(char *fileName);

/* Given a .ITF file's name, read in the data frames from the file,
 * convert the data in them to a malloc'ed array of per-channel 
 * floats. If the corresponding .ITF.ITA file can be opened, read it
 * and use its gain settings to convert the per-channel data from
 * raw D-A values to microvolts.
 *
 * Also read the parallel port data into the malloc'ed array and point
 * *parallelPortData at the array.
 */
struct itekChannel * readAmpBinary(char *fileName, unsigned char **parallelPortData);


/*
 * Read the Itek card info from the .ITF.ITA file, which is
 * a text file with lines like these:
 *
 *	Card.0.on=true
 *	Card.0.lpf=0
 *	Card.0.gain=2
 *	Card.1.on=true
 *	Card.1.lpf=0
 *	Card.1.gain=2
 *	...
 *	Card.15.gain=2
 *
 * 'on' indicates if the card is on (true) or off (false).
 * 'lpf' indicates if the low-pass filter is set to 100 Hz (0) or
 *	300 Hz (1). CHECK THIS NOT REALLY SURE WHICH SETTING IS WHAT
 * 'gain' indicates the gain setting: 400 (0), 10000 (1), 2000 (2).
 */

struct itekCardInfo * readITAFile(char *itaFilename);


/* Attempt to open the .ITF.ITA file corresponding to .ITF file
 * 'inputFilename'. If can open and read the .ITF.ITA file, scale
 * the input data from 24-bit integers (producted by the amps' D-A
 * chips) to Volts then to microVolts and scale by amps' gains.
 *
 * Return 0 on success and modify values in 'channels' array, or
 * 1 on failure, and leave 'channels' unchanged.
 */

int applyGains(struct itekChannel *channels, char *inputFilename);
