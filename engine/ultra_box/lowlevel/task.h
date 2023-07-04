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
#pragma once

/*--------------------------------------------------------------------------------------------------------------------*/

#define UBX_TASK_SET_DATA(ostaskptr, startptr, endptr) ( \
	(ostaskptr)->t.data_ptr = (u64*)(startptr), \
	(ostaskptr)->t.data_size = (u32)(endptr) - (u32)(startptr) \
)

#define UBX_TASK_SET_YIELD_DATA(ostaskptr, startptr, endptr) ( \
	(ostaskptr)->t.yield_data = (u64*)(startptr), \
	(ostaskptr)->t.yield_data_size = (u32)(endptr) - (u32)(startptr) \
)

#define UBX_TASK_SET_BOOT_UCODE(ostaskptr, startptr, endptr) ( \
	(ostaskptr)->t.ucode_boot = (u64*)(startptr), \
	(ostaskptr)->t.ucode_boot_size = (u32)(endptr) - (u32)(startptr) \
)

#define UBX_TASK_SET_RSP_UCODE(ostaskptr, startptr, endptr) ( \
	(ostaskptr)->t.ucode = (u64*)(startptr), \
	(ostaskptr)->t.ucode_size = (u32)(endptr) - (u32)(startptr) \
)

#define UBX_TASK_SET_RSP_UCODE_DATA(ostaskptr, startptr, endptr) ( \
	(ostaskptr)->t.ucode_data = (u64*)(startptr), \
	(ostaskptr)->t.ucode_data_size = (u32)(endptr) - (u32)(startptr) \
)

/*--------------------------------------------------------------------------------------------------------------------*/