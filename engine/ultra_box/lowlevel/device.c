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

#include "device.h"

#include <string.h>

/*--------------------------------------------------------------------------------------------------------------------*/

UbxDeviceData gUbxDevice;

/*--------------------------------------------------------------------------------------------------------------------*/

void _UbxDeviceSetDefaults()
{
	/* Clear the data structure. */
	memset(&gUbxDevice, 0, sizeof(gUbxDevice));

	/* Generate handles for interacting with the game storage media. */
	gUbxDevice.pCartRom = osCartRomInit();
	gUbxDevice.pLeoDisk = osLeoDiskInit();
	gUbxDevice.pDriveRom = osDriveRomInit();
}

/*--------------------------------------------------------------------------------------------------------------------*/

void _UbxDeviceInitialize()
{
	/* Create the message queue for handling media access. */
	osCreatePiManager(OS_PRIORITY_PIMGR, &gUbxDevice.msgQueue, gUbxDevice.pMsgBuffer, (s32) gUbxDevice.msgLength);
}

/*--------------------------------------------------------------------------------------------------------------------*/
