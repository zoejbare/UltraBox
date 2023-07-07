//
// Copyright (c) 2023, Zoe J. Bare
//
// Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
// documentation files (the "Software"), to deal in the Software without restriction, including without limitation
// the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
// and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all copies or substantial portions
// of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
// TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
// THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
// CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
// IN THE SOFTWARE.
//
#pragma once

//----------------------------------------------------------------------------------------------------------------------

#include <stdio.h>

//----------------------------------------------------------------------------------------------------------------------

enum class LogLevel
{
	Quiet,
	Normal,
	Verbose,
};

//----------------------------------------------------------------------------------------------------------------------

extern LogLevel gLogLevel;

//----------------------------------------------------------------------------------------------------------------------

#define LOG_ERROR(msg) fprintf(stderr, "[ERROR] " msg "\n")
#define LOG_ERROR_FMT(fmt, ...) fprintf(stderr, "[ERROR] " fmt "\n", __VA_ARGS__)

#define LOG_WARN(msg) fprintf(stderr, "[WARNING] " msg "\n")
#define LOG_WARN_FMT(fmt, ...) fprintf(stderr, "[WARNING] " fmt "\n", __VA_ARGS__)

#define LOG_INFO(msg) if(gLogLevel != LogLevel::Quiet) { fprintf(stdout, msg "\n"); }
#define LOG_INFO_FMT(fmt, ...) if(gLogLevel != LogLevel::Quiet) { fprintf(stdout, fmt "\n", __VA_ARGS__); }

#define LOG_VERBOSE(msg) if(gLogLevel == LogLevel::Verbose) { fprintf(stdout, msg "\n"); }
#define LOG_VERBOSE_FMT(fmt, ...) if(gLogLevel == LogLevel::Verbose) { fprintf(stdout, fmt "\n", __VA_ARGS__); }

//----------------------------------------------------------------------------------------------------------------------
