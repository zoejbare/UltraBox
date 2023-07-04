#
# Copyright (c) 2023, Zoe J. Bare
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions
# of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
# TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
#

import sys

from . import log_level

# Set the default log level.
_LOG_LEVEL = log_level.INFO

def _handleMessage(level, message):
	global _LOG_LEVEL
	if level > _LOG_LEVEL:
		return

	log_level.validateLogLevel(level)

	tag = log_level.levelToString(level)
	output = f"[{tag}] {message}"
	stream = sys.stdout

	if level <= log_level.WARNING:
		stream = sys.stderr

	print(output, file=stream)
	stream.flush()

def setLevel(level):
	log_level.validateLogLevel(level)

	# Override the log level.
	global _LOG_LEVEL
	_LOG_LEVEL = level

def fatal(message):
	_handleMessage(log_level.FATAL, message)
	sys.exit(1)

def error(message):
	_handleMessage(log_level.ERROR, message)

def warning(message):
	_handleMessage(log_level.WARNING, message)

def info(message):
	_handleMessage(log_level.INFO, message)

def verbose(message):
	_handleMessage(log_level.VERBOSE, message)

def rawMessage(message):
	print(message, file=sys.stdout, end="")
	sys.stdout.flush()

def rawError(message):
	print(message, file=sys.stderr, end="")
	sys.stderr.flush()