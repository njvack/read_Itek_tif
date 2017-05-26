/* READITF.C
 *
 * Copyright 2016 Board of Regents of the University of Wisconsin System
 *
 * This app reads in the specified ItekAnalyze .ITF files (and, if present,
 * the matching .ITF.ITA file) and outputs their data to the specified
 * comma-separated value human- and Excel-readable .CSV file. If the .ITF.ITA
 * file is present and readable, the output values will be in scaled and
 * gain-adjusted mV, otherwise they wil be raw A-D converter values (integers).
 *
 * usage: readitf <datafile.itf> [<outputfile.csv>]
 *
 * <datafile.itf> should be a file produced by the ItekAnalyse EMG data
 * collection app.\n");
 * 
 * If <outputfile.csv> is not specified, the raw Itek data frames will be
 * dumped to stdout in human-readable format.
 *
 * Version history:
 * 2016-02-15	John Koger	Initial version.
 * 2016-12-21	John Koger	Added output of parallel port data.
 */

 #define READITF_VERSION	"1.01"
 
#include "readitf.h"

/* Comment out this #define to compile a linkable .o file of these routines. */
#define MAIN


/* Check to see if a data frame has the packet-start chars '1' - '7'
 * in the expected places. Return 1 if things look good, 0 if they don't.
 */
int checkItekDataFrame(struct itekDataFrame *df)
{
	if (df->packet1 != '1')
	{
		printf("Ack! Data frame failed packet 1 check!\n");
		dumpItekDataFrame(df);
		return(1);
	}
	if (df->packet2 != '2')
	{
		printf("Ack! Data frame failed packet 2 check!\n");
		dumpItekDataFrame(df);
		return(1);
	}
	if (df->packet3 != '3')
	{
		printf("Ack! Data frame failed packet 3 check!\n");
		dumpItekDataFrame(df);
		return(1);
	}
	if (df->packet4 != '4')
	{
		printf("Ack! Data frame failed packet 4 check!\n");
		dumpItekDataFrame(df);
		return(1);
	}
	if (df->packet5 != '5')
	{
		printf("Ack! Data frame failed packet 5 check!\n");
		dumpItekDataFrame(df);
		return(1);
	}
	if (df->packet6 != '6')
	{
		printf("Ack! Data frame failed packet 6 check!\n");
		dumpItekDataFrame(df);
		return(1);
	}
	if (df->packet7 != '7')
	{
		printf("Ack! Data frame failed packet 7 check!\n");
		dumpItekDataFrame(df);
		return(1);
	}

	return(0);
}


/* Read in all of the data frames in a .ITF file. If data frames
 * are successfully read, return a pointer to a malloc'ed array of
 * data frames, or NULL if the file read failed. Set the long pointed
 * to by *numSamples to the number of data frames read in. *numSamples
 * equates to the number of samples per data channel read in.
 */
struct itekDataFrame * readItekData(char *fileName, long *numSamples)
{
	FILE	*fp;
	long	fileLength, numFramesInFile, i, numBadFrames;
	size_t	allocBytes, numBytesRead, startOffset;
	struct itekDataFrame
		*dataFrames;
	char	tmp[400];

	fp = fopen(fileName, "rb");
	if (fp == NULL)
	{
		printf("readItekData: unable to open file '%s' for read.\n",
			fileName);
		return(NULL);
	}

	fseek(fp, 0L, SEEK_END);
	fileLength = ftell(fp);
	fseek(fp, 0L, SEEK_SET);

	/* Sometimes the .ITF file seems to start with some non-record
	 * stuff. Skip past it. If the first record doesn't start
	 * within the first 400 chars, punt.
	 */
	numBytesRead = fread(tmp, sizeof(char), 400, fp);
	for (startOffset = 0; startOffset < 400; startOffset++)
	{
		if (tmp[startOffset] == '1')
			break;
	}

	if (startOffset >= 400)
	{
		printf("readItekData: unable to find first frame in '%s'.\n",
			fileName);
		fclose(fp);
		return(NULL);
	}
	else if (startOffset > 0)
	{
		printf("readItekData: skipping %ld bytes to first frame.\n",
			startOffset);
	}

	fseek(fp, startOffset, SEEK_SET);

	fileLength -= startOffset;

	numFramesInFile = fileLength / sizeof(struct itekDataFrame);
	if (numFramesInFile < 1)
	{
		fclose(fp);
		printf("readItekData: file '%s' >= %d bytes long.\n",
			fileName, sizeof(struct itekDataFrame));
		return(NULL);
	}

	allocBytes = numFramesInFile * sizeof(struct itekDataFrame);
	dataFrames = malloc(allocBytes);

	if (dataFrames == NULL)
	{
		fclose(fp);
		printf("readItekData: failed to allocate memory for data.\n");
		return(NULL);
	}

	printf("Reading in data...\n");
	numBytesRead = fread(dataFrames, sizeof(struct itekDataFrame),
		numFramesInFile, fp);
	numBytesRead *= sizeof(struct itekDataFrame);
	printf("Read of %ld bytes complete...\n", numBytesRead);

	if (numBytesRead < allocBytes)
	{
		fclose(fp);
		printf("readItekData: failed to read data.\n");
		printf("Bytes expected to read: %ld\n", allocBytes);
		printf("Bytes actually read: %ld\n", numBytesRead);
		return(NULL);
	}
	
	fclose(fp);

	numBadFrames = 0;
	for (i = 0; i < numFramesInFile; i++)
	{
		if (checkItekDataFrame(&(dataFrames[i])) != 0)
		{
			printf("Data frame %ld failed check!\n", i);
			numBadFrames++;
		}
		if (numBadFrames > 1000)
		{
			printf("%ld data frames failed check! Giving up!\n",
				numBadFrames);
			free(dataFrames);
			return(NULL);
		}
	}

	printf("Check of %ld data frames OK.\n", i);
	
	*numSamples = numFramesInFile;
	return(dataFrames);
}


/* Convert a 24-bit big-endian 2's-complement signed integer to a
 * regular integer and then to a float.
 */
float itekFloat(struct threeByteInt *itekValue)
{
	static unsigned char
		u[4];
	int	i, *j;

	u[2] = itekValue->msb;

	/* If the top bit of MSB is set, it's a negative number.
	 * Force the 'top byte' of the resulting int to be negative.
	 */
	if ((u[2] & 0x80) != 0)
		u[3] = 0xFF;
	else
		u[3] = 0;

	u[1] = itekValue->middle;
	u[0] = itekValue->lsb;

	j = (int *) u;
	i = j[0];

	/*
	if (i != 0)
	{
		printf("itekFloat(0x%0X, 0x%0X, 0x%0X) = %d.\n",
			itekValue->msb, itekValue->middle, itekValue->lsb, i);
	}
	*/

	return((float) i);
}


/* Given a data frame, extract the data from the frame for
 * the parallel port.
 */
unsigned char itekHardwareChannelParallelPortData(struct itekDataFrame *df)
{
	return(df->parallelPortPins);
}


/* Given a data frame, extract the data from the frame for
 * a given channel, 0 - 127.
 */
float itekHardwareChannelData(int chanNum, struct itekDataFrame *df)
{
	int	i;

	if ((chanNum >= 109) && (chanNum <= 127))
	{
		i = 127 - chanNum;
		/* printf("Mapping chanNum %d to 127-109 index %d\n", chanNum, i); */
		return(itekFloat(&(df->chans127to109[i])));
	}
	else if ((chanNum >= 89) && (chanNum <= 108))
	{
		i = 108 - chanNum;
		/* printf("Mapping chanNum %d to 108-89 index %d\n", chanNum, i); */
		return(itekFloat(&(df->chans108to89[i])));
	}
	else if ((chanNum >= 69) && (chanNum <= 88))
	{
		i = 88 - chanNum;
		/* printf("Mapping chanNum %d to 88-69 index %d\n", chanNum, i); */
		return(itekFloat(&(df->chans88to69[i])));
	}
	else if ((chanNum >= 49) && (chanNum <= 68))
	{
		i = 68 - chanNum;
		/* printf("Mapping chanNum %d to 68-49 index %d\n", chanNum, i); */
		return(itekFloat(&(df->chans68to49[i])));
	}
	else if ((chanNum >= 29) && (chanNum <= 48))
	{
		i = 48 - chanNum;
		/* printf("Mapping chanNum %d to 48-29 index %d\n", chanNum, i); */
		return(itekFloat(&(df->chans48to29[i])));
	}
	else if ((chanNum >= 9) && (chanNum <= 28))
	{
		i = 28 - chanNum;
		/* printf("Mapping chanNum %d to 28-9 index %d\n", chanNum, i); */
		return(itekFloat(&(df->chans28to09[i])));
	}
	else if ((chanNum >= 0) && (chanNum <= 8))
	{
		i = 8 - chanNum;
		/* printf("Mapping chanNum %d to 8-0 index %d\n", chanNum, i); */
		return(itekFloat(&(df->chans08to00[i])));
	}
	else
	{
		printf("Ack! Invalid chanNum %d!\n", chanNum);
		return(0.0);
	}
}


/* Given a data frame, dump its contents to stdout in a human-readable
 * format.
 */
void dumpItekDataFrame(struct itekDataFrame *df)
{
	int	i;

	printf("    Packet 1 ID: '%c',", df->packet1);
	printf(" Record #: %u.", (unsigned int) df->recordNumber);
	printf(" Error flags: 0x%X.", df->errorFlags);
	printf(" Status flags: 0x%X\n", df->statusFlags);
	printf("   Parallel port: 0x%X,", df->parallelPortPins);
	printf(" TR: 0x%X 0x%X\n    ", df->tr.msb, df->tr.lsb);

	for (i = 0; i < 19; i++)
	{
		printf("Ch %d: 0x%X 0x%X 0x%X, ", 127 - i,
			df->chans127to109[i].msb,
			df->chans127to109[i].middle,
			df->chans127to109[i].lsb);
	}

	printf("\n    Packet 2 ID: '%c', ", df->packet2);
	for (i = 0; i < 20; i++)
	{
		printf("Ch %d: 0x%X 0x%X 0x%X, ", 108 - i,
			df->chans108to89[i].msb,
			df->chans108to89[i].middle,
			df->chans108to89[i].lsb);
	}

	printf("\n    Packet 3 ID: '%c', ", df->packet3);
	for (i = 0; i < 20; i++)
	{
		printf("Ch %d: 0x%X 0x%X 0x%X, ", 88 - i,
			df->chans88to69[i].msb,
			df->chans88to69[i].middle,
			df->chans88to69[i].lsb);
	}

	printf("\n    Packet 4 ID: '%c', ", df->packet4);
	for (i = 0; i < 20; i++)
	{
		printf("Ch %d: 0x%X 0x%X 0x%X, ", 68 - i,
			df->chans68to49[i].msb,
			df->chans68to49[i].middle,
			df->chans68to49[i].lsb);
	}

	printf("\n    Packet 5 ID: '%c', ", df->packet5);
	for (i = 0; i < 20; i++)
	{
		printf("Ch %d: 0x%X 0x%X 0x%X, ", 48 - i,
			df->chans48to29[i].msb,
			df->chans48to29[i].middle,
			df->chans48to29[i].lsb);
	}

	printf("\n    Packet 6 ID: '%c', ", df->packet6);
	for (i = 0; i < 20; i++)
	{
		printf("Ch %d: 0x%X 0x%X 0x%X, ", 28 - i,
			df->chans28to09[i].msb,
			df->chans28to09[i].middle,
			df->chans28to09[i].lsb);
	}

	printf("\n    Packet 7 ID: '%c', ", df->packet7);
	for (i = 0; i < 9; i++)
	{
		printf("Ch %d: 0x%X 0x%X 0x%X, ", 8 - i,
			df->chans08to00[i].msb,
			df->chans08to00[i].middle,
			df->chans08to00[i].lsb);
	}

	printf("\n    Record chk: %u,", (unsigned int) df->recordNumberCheck);
	printf("  Frame end: 0x%X 0x%X.\n", df->frameTerminator[0],
		df->frameTerminator[1]);
}


/* Given an array of data frames, dump their contents to stdout in a
 * human-readable format.
 */
void dumpItekDataFrames(char *fileName)
{
	struct itekDataFrame
		*dataFrames;
	long	numFramesRead, i, j, k;

	dataFrames = readItekData(fileName, &numFramesRead);
	if (dataFrames == NULL)
	{
		printf("dumpItekDataFrames: Can't read file '%s'.\n", fileName);
		return;
	}

	for (i = 0; i < numFramesRead; i++)
	{
		printf("\nData Frame %ld:\n", i);
		dumpItekDataFrame(&(dataFrames[i]));
	}
}


/* Given a .ITF file's name, read in the data frames from the file,
 * convert the data in them to a malloc'ed array of per-channel 
 * floats. If the corresponding .ITF.ITA file can be opened, read it
 * and use its gain settings to convert the per-channel data from
 * raw D-A values to microvolts.
 *
 * Also read the parallel port data into the malloc'ed array and point
 * *parallelPortData at the array.
 */
struct itekChannel * readAmpBinary(char *fileName, unsigned char **parallelPortData)
{
	struct itekDataFrame
		*dataFrames;
	struct itekChannel
		*channels;
	long	numFramesRead, i, j, k;
	size_t	allocBytes, ppAllocBytes;

	dataFrames = readItekData(fileName, &numFramesRead);
	if (dataFrames == NULL)
	{
		printf("readAmpBinary: Can't read file '%s'.\n", fileName);
		return(NULL);
	}

	printf("Looks like we read %ld frames.\n", numFramesRead);

	allocBytes = ITEK_MAX_CHANS * sizeof(struct itekChannel);
	channels = malloc(allocBytes);

	if (channels == NULL)
	{
		printf("readAmpBinary: failed to allocate memory for data.\n");
		return(NULL);
	}

	printf("Channel malloc OK.\n");

	allocBytes = numFramesRead * sizeof(float);
	ppAllocBytes = numFramesRead * sizeof(unsigned char);

	*parallelPortData = malloc(ppAllocBytes);
	if (*parallelPortData == NULL)
	{
		printf("readAmpBinary: can't allocate parallel port data.\n");
		free(channels);
		return(NULL);
	}

	for (j = 0; j < numFramesRead; j++)
	{
		(*parallelPortData)[j] = itekHardwareChannelParallelPortData(&(dataFrames[j]));
	}

	for (i = 0; i < ITEK_MAX_CHANS; i++)
	{
		channels[i].numSamples = numFramesRead;
		channels[i].data = malloc(allocBytes);
		if (channels[i].data == NULL)
		{
			printf("readAmpBinary: can't allocate chan %d data.\n",
				i);
			for (j = 0; j < i; j++)
				free(channels[i].data);
			free(channels);
			free(parallelPortData);
			return(NULL);
		}

		/* printf("Channel %ld data malloc OK.\n", i); */

		for (j = 0; j < numFramesRead; j++)
		{
			channels[i].data[j] = itekHardwareChannelData(i,
				&(dataFrames[j]));
		}

		/* printf("Channel %ld value assignments OK.\n", i); */
	}

	free(dataFrames);

	printf("readAmpChannels() done.\n");
	return(channels);
}


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

struct itekCardInfo * readITAFile(char *itaFilename)
{
	struct itekCardInfo
		*cards;
	FILE	*fp;
	int	numThingsScanned, cardNum, i, j;
	char	text[2048], value[2048];

	fp = fopen(itaFilename, "r");
	if (fp == NULL)
	{
		printf("readITAFile: Can't open .ITA file '%s' for read.\n",
			itaFilename);
		return(NULL);
	}

	cards = malloc(ITEK_MAX_CARDS * sizeof(struct itekCardInfo));
	if (cards == NULL)
	{
		printf("readITAFile: Can't allocate card info memory.\n");
		fclose(fp);
		return(NULL);
	}

	for (i = 0; i < ITEK_MAX_CARDS; i++)
	{
		cards[i].onOff = 0;
		cards[i].rawLowPassFilter = 0;
		cards[i].rawGain = 0;
		cards[i].lowPassFilter = 100.0;
		cards[i].gain = 450.0;
	}

	while (fgets(text, 2047, fp) != NULL)
	{
		if (strncmp(text, "Card.", 5) != 0)
		{
			printf("readITAFile: unexpected line '%s', ignored.\n",
				text);
			continue;
		}
		if (strstr(text, "on") != NULL)
		{
			numThingsScanned =
				sscanf(text, "Card.%d.on=%s", &cardNum, value);
			if (numThingsScanned != 2)
			{
				printf("readITAFile: can't parse '%s'.\n",
					text);
				continue;
			}
			if ((cardNum < 0) || (cardNum > 15))
			{
				printf("readITAFile: bad card # in '%s'.\n",
					text);
				continue;
			}
			if (strncmp(value, "true", 4) == 0)
				cards[cardNum].onOff = 1;
			else
				cards[cardNum].onOff = 0;
		}
		else if (strstr(text, "lpf") != NULL)
		{
			numThingsScanned =
				sscanf(text, "Card.%d.lpf=%s", &cardNum, value);
			if (numThingsScanned != 2)
			{
				printf("readITAFile: can't parse '%s'.\n",
					text);
				continue;
			}
			if ((cardNum < 0) || (cardNum > 15))
			{
				printf("readITAFile: bad card # in '%s'.\n",
					text);
				continue;
			}
			j = atoi(value);
			if (j == 0)
			{
				cards[cardNum].rawLowPassFilter = 0;
				cards[cardNum].lowPassFilter = 100.0;
			}
			else
			{
				cards[cardNum].rawLowPassFilter = 1;
				cards[cardNum].lowPassFilter = 300.0;
			}
		}
		else if (strstr(text, "gain") != NULL)
		{
			numThingsScanned =
				sscanf(text, "Card.%d.gain=%s",
				&cardNum, value);
			if (numThingsScanned != 2)
			{
				printf("readITAFile: can't parse '%s'.\n",
					text);
				continue;
			}
			if ((cardNum < 0) || (cardNum > 15))
			{
				printf("readITAFile: bad card # in '%s'.\n",
					text);
				continue;
			}
			j = atoi(value);
			if (j == 0)
			{
				cards[cardNum].rawGain = 0;
				cards[cardNum].gain = 400.0;
			}
			else if (j == 1)
			{
				cards[cardNum].rawGain = 1;
				cards[cardNum].gain = 10000.0;
			}
			else if (j == 2)
			{
				cards[cardNum].rawGain = 2;
				cards[cardNum].gain = 2000.0;
			}
		}
		else
		{
			printf("readITAFile: can't parse line '%s', ignored.\n",
				text);
			continue;
		}
	}

	fclose(fp);

	return(cards);
}


/* Attempt to open the .ITF.ITA file corresponding to .ITF file
 * 'inputFilename'. If can open and read the .ITF.ITA file, scale
 * the input data from 24-bit integers (producted by the amps' D-A
 * chips) to Volts then to microVolts and scale by amps' gains.
 *
 * Return 0 on success and modify values in 'channels' array, or
 * 1 on failure, and leave 'channels' unchanged.
 */

int applyGains(struct itekChannel *channels, char *inputFilename)
{
	struct itekCardInfo
		*cards;
	float	Vref = V_REF,
		bitResolution = BIT_RES,
		microV = MICROV,
		scaleFactor;
	long	i, j, k;
	char	itaFilename[2048];

	sprintf(itaFilename, "%s.ita", inputFilename);
	cards = readITAFile(itaFilename);
	if (cards == NULL)
	{
		sprintf(itaFilename, "%s.ITA", inputFilename);
		cards = readITAFile(itaFilename);
	}

	if (cards == NULL)
		return(1);

	printf("Applying gains from '%s' to data...\n", itaFilename);
	for (k = 0; k < ITEK_MAX_CARDS; k++)
	{
		printf("    Card %d gain: %f.\n", k, cards[k].gain);

		/* Start with 24-bit signed integer, max/min value
		 * is += bitResolution (2^24 / 2 = 2^23 - 1). Multiply
		 * by Vref (5.0V) and divide by bitResolution to
		 * convert to Volts.
		 *
		 * Divide by card's gain factor to account for it.
		 *
		 * Multiply by microV (10^6) to convert to uV.
		 */
		scaleFactor = (Vref * microV) / (bitResolution * cards[k].gain);

		for (i = (k * 8); i < (k * 8) + 8; i++)
		{
			for (j = 0; j < channels[i].numSamples; j++)
			{
				channels[i].data[j] *= scaleFactor;
			}
		}
	}

	return(0);
}


/* Write channel data out to a .CSV human- and Excel-readable
 * comma-separated-value text file. 1 row (line) per channel,
 * 1 column per data sample per column, with commas between the samples.
 *
 * Return 0 on success, 1 on file open failure.
 */

int writeChannelsToCSV(struct itekChannel *channels, unsigned char *parallelPortData, char *outputFilename)
{
	FILE	*outFP;
	long	i, j;

	printf("Writing data to .CSV file '%s'...\n", outputFilename);

	outFP = fopen(outputFilename, "w");
	if (outFP == NULL)
	{
		printf("writeChannelsToCSV(): could not open output .csv file '%s'.\n",
			outputFilename);
		return(1);
	}

	printf("Channel: ");
	fflush(stdout);
	for (i = 0; i < ITEK_MAX_CHANS; i++)
	{
		for (j = 0; j < channels[i].numSamples; j++)
		{
			if (j == 0)
				fprintf(outFP, "%f", channels[i].data[j]);
			else
				fprintf(outFP, ", %f", channels[i].data[j]);
		}
		fprintf(outFP, "\n");
		printf("%ld ", i);
		fflush(stdout);
	}

	/* Add the parallel port data on the end as if it's another data channel. Which it is, just like Pluto is a planet! */
	for (j = 0; j < channels[0].numSamples; j++)
	{
		if (j == 0)
			fprintf(outFP, "%u", (unsigned int) parallelPortData[j]);
		else
			fprintf(outFP, ", %u", (unsigned int) parallelPortData[j]);
	}
	fprintf(outFP, "\n");
	printf("parallel-port\n");
	fflush(stdout);

	fclose(outFP);
	return(0);
}


#ifdef MAIN

main(int argc, char *argv[])
{
	struct itekChannel
		*channels;
	static unsigned char
		*parallelPortData;
	char	*inputFilename, *outputFilename;
	long	i, j, k;

	if (sizeof(struct itekDataFrame) != 400)
	{
		printf("sizeof(itekDataFrame) should be 400, but is %d.\n",
			sizeof(struct itekDataFrame));
		exit(1);
	}

	if (argc < 2)
	{
		printf("\nusage: %s <datafile.itf> [<outputfile.csv>]\n",
			argv[0]);
		printf("\n<datafile.itf> should be a file produced by\n");
		printf("the ItekAnalyse EMG data collection app.\n");
		printf("If a corresponding .itf.ita file is present,\n");
		printf("output values will be in mV, otherwise they\n");
		printf("will be in raw A-D converter 24-bit integers.\n");
		printf("\n<outputfile.csv> will be a comma-separated\n");
		printf("value text file of the input data.\n");
		printf("\nIf <outputfile.csv> is not specified, the\n");
		printf("raw Itek data frames will be dumped to stdout\n");
		printf("in human-readable format.\n");
		printf("\nBuild version: %s. %s - %s\n", READITF_VERSION, __DATE__, __TIME__);
		exit(1);
	}

	inputFilename = argv[1];

	if (argc == 2)
	{
		dumpItekDataFrames(inputFilename);
		exit(0);
	}

	outputFilename = argv[2];

	channels = readAmpBinary(inputFilename, &parallelPortData);
	if (channels == NULL)
	{
		printf("%s could not read input .itf file '%s'.\n",
			argv[0], inputFilename);
		exit(1);
	}

	if (applyGains(channels, inputFilename) != 0)
	{
		printf("Can't find .ITF.ITA file for '%s'.\n",
			inputFilename);
		printf("Written data values NOT converted to microVolts or");
		printf("scaled to account for amp gains.\n");
	}

	writeChannelsToCSV(channels, parallelPortData, outputFilename);

	printf("Done!\n");
	exit(0);
}

#endif
