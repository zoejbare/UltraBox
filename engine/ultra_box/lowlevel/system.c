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

#include "system.h"

#include <string.h>

/*--------------------------------------------------------------------------------------------------------------------*/

UbxSystemData gUbxSystem;

/*--------------------------------------------------------------------------------------------------------------------*/

void _UbxSystemSetDefaults()
{
	/* Clear the data structure. */
	memset(&gUbxSystem, 0, sizeof(gUbxSystem));

	/* Set the default lengths for each system message system. */
	gUbxSystem.dmaMsgQueueLength = 1;
	gUbxSystem.rcpMsgQueueLength = 1;
	gUbxSystem.rdpMsgQueueLength = 1;
}

/*--------------------------------------------------------------------------------------------------------------------*/

void _UbxSystemInitialize()
{
	OSMesg dummyMsg;
	memset(&dummyMsg, 0, sizeof(dummyMsg));

	/* Create the DMA message queue. */
	osCreateMesgQueue(&gUbxSystem.dmaMsgQueue, &gUbxSystem.dmaMsg, gUbxSystem.dmaMsgQueueLength);

	/* Create the RCP message queue. */
	osCreateMesgQueue(&gUbxSystem.rcpMsgQueue, &gUbxSystem.rcpMsg, gUbxSystem.rcpMsgQueueLength);
	osSetEventMesg(OS_EVENT_SP, &gUbxSystem.rcpMsgQueue, dummyMsg);

	/* Create the RDP message queue. */
	osCreateMesgQueue(&gUbxSystem.rdpMsgQueue, &gUbxSystem.rdpMsg, gUbxSystem.rdpMsgQueueLength);
	osSetEventMesg(OS_EVENT_DP, &gUbxSystem.rdpMsgQueue, dummyMsg);
}

/*--------------------------------------------------------------------------------------------------------------------*/
