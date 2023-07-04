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

#include "lowlevel/device.h"
#include "lowlevel/system.h"
#include "lowlevel/video.h"

#include <os.h>

#include <stdint.h>

/*--------------------------------------------------------------------------------------------------------------------*/

#define IDLE_THREAD_ID 1
#define MAIN_THREAD_ID 2

/*--------------------------------------------------------------------------------------------------------------------*/

static OSThread idleThread;
static OSThread mainThread;

extern u8 _idle_stack_end[];
extern u8 _main_stack_end[];

/*--------------------------------------------------------------------------------------------------------------------*/

extern void OnGameBoot();
extern void OnGameInitialize();
extern void OnGameMainLoop(void*);

/*--------------------------------------------------------------------------------------------------------------------*/

__attribute__((noreturn)) void idle(void*)
{
	/* Initialize the engine components. */
	_UbxSystemInitialize();
	_UbxVideoInitialize();
	_UbxDeviceInitialize();

	/* Run any startup initialization required by the game. */
	OnGameInitialize();

	/* Start the main thread. */
	osCreateThread(&mainThread, MAIN_THREAD_ID, OnGameMainLoop, NULL, _main_stack_end, 10);
	osStartThread(&mainThread);

	/* De-prioritize the thread so this becomes the idle thread. */
	osSetThreadPri(NULL, 0);

	/* We intentionally spin forever to give this thread time to permanently yield to the main thread. */
	for(;;) {}

	__builtin_unreachable();
}

/*--------------------------------------------------------------------------------------------------------------------*/

__attribute__((noreturn)) void boot()
{
	/* Initialize the N64 hardware. */
	osInitialize();

	/* Fill all global data objects with their default values. */
	_UbxSystemSetDefaults();
	_UbxVideoSetDefaults();
	_UbxDeviceSetDefaults();

	/* Handle game-specific initialization that needs to be done at boot-time prior to engine initialization. */
	OnGameBoot();

	/* Start the thread that will be used for initialization and kicking off the main thread. */
	osCreateThread(&idleThread, IDLE_THREAD_ID, idle, NULL, _idle_stack_end, 10);
	osStartThread(&idleThread);

	__builtin_unreachable();
}

/*--------------------------------------------------------------------------------------------------------------------*/
