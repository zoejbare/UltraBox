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

ENTRY(_start)

MEMORY {
	rom (R) : ORIGIN = 0, LENGTH = 64M
	ram (RWX) : ORIGIN = 0x80000400, LENGTH = 8M - 0x400
}

SECTIONS
{
	.header :
	{
		LONG(0x80371240)
		LONG(0x0000000f)
		LONG(0x80000400)
		LONG(0x0000144c)
		. = 0x1000;
	} >rom

	.text :
	{
		_text_start = .;
		*(.text.entry)
		*(.text .text.*)
		*(.rodata .rodata.*)
		*(.data .data.*)
		_text_end = .;
	} >ram AT>rom

	.bss (NOLOAD) : ALIGN(16)
	{
		_bss_start = .;
		*(.bss .bss.*)
		*(COMMON)
		*(.scommon .scommon.*)
		_bss_end = .;
	} >ram

	STACK_SIZE = 8K;

	.stack (NOLOAD) : ALIGN(16)
	{
		. += STACK_SIZE;
		. = ALIGN(8);
		_boot_stack_end = .;
		_main_stack_end = .;

		. += STACK_SIZE;
		. = ALIGN(8);
		_idle_stack_end = .;
	} >ram

	/DISCARD/ :
	{
		*(*)
	}
}