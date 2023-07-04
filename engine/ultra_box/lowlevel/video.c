/*
 * Copyright (c) 2023, Zoe J. Bare
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the "Software"), to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
 * and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or substantial portions
 * of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
 * TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
 * CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */

#include "video.h"

#include <string.h>

/*--------------------------------------------------------------------------------------------------------------------*/

UbxVideoData gUbxVideo;

/*--------------------------------------------------------------------------------------------------------------------*/

void _UbxVideoSetDefaults()
{
	/* Clear the data structure. */
	memset(&gUbxVideo, 0, sizeof(gUbxVideo));

	/* Set the default message queue length. */
	gUbxVideo.retraceMsgQueueLength = 1;
}

/*--------------------------------------------------------------------------------------------------------------------*/

void _UbxVideoInitialize()
{
	OSMesg dummyMsg;
	memset(&dummyMsg, 0, sizeof(dummyMsg));

	/* Initialize the video interface. */
	osCreateViManager(OS_PRIORITY_VIMGR);

	/* Set the VI mode to initialize the display. */
	osViSetMode(&osViModeTable[gUbxVideo.viModeIndex]);

	/* Configure the VI interface. */
	osViSetSpecialFeatures(OS_VI_DITHER_FILTER_OFF);
	osViSetSpecialFeatures(OS_VI_DIVOT_OFF);

	/* Create the message queue for the vertical retrace interrupt. */
	osCreateMesgQueue(&gUbxVideo.retraceMsgQueue, &gUbxVideo.retraceMsg, gUbxVideo.retraceMsgQueueLength);
	osViSetEvent(&gUbxVideo.retraceMsgQueue, dummyMsg, 1);
}

/*--------------------------------------------------------------------------------------------------------------------*/
