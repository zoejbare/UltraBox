#!/usr/bin/env python3
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

import argparse
import datetime
import os
import platform
import sys
import time

from toolchain_setup.bootstrapper.config import Config
from toolchain_setup.bootstrapper.toolchain import buildToolchain
from toolchain_setup.util import log_level, log

_REPO_ROOT_PATH = os.path.abspath(f"{os.path.dirname(__file__)}/..")

def _parseCommandLine():
	parser = argparse.ArgumentParser(description="Utility for bootstrapping a modern N64 development toolchain")

	parser.add_argument(
		"--force-download",
		action="store_true",
		help="Force the zipped packages to download rather than downloading only on a checksum mismatch",
	)

	parser.add_argument(
		"-j", "--jobs",
		action="store",
		type=int,
		default=sys.maxsize,
		help="Limit the maximum number of job threads for building the toolchain (uses the total number of CPU cores available by default)",
	)

	parser.add_argument(
		"--verbose",
		action="store_true",
		help="Enable verbose logging",
	)

	parser.add_argument(
		"-w", "--windows-cross-compile",
		action="store_true",
		help="Build the toolchain for Windows (see README.md for more information)",
	)

	return parser.parse_args()

def main():
	args = _parseCommandLine()

	config = Config.getInstance()
	config.cpuCoreCount = args.jobs
	config.forceDownload = args.force_download
	config.windowsCrossCompile = args.windows_cross_compile

	# The only way to get a Windows build is to do a cross compile from Linux.
	toolchainPlatform = "windows" if config.windowsCrossCompile else platform.system().lower()

	config.cachePath = os.path.normpath(f"{_REPO_ROOT_PATH}/_sdkcache")
	config.installPath = os.path.normpath(f"{_REPO_ROOT_PATH}/toolchain/{toolchainPlatform}")

	log.setLevel(log_level.VERBOSE if args.verbose else log_level.INFO)

	startTime = time.perf_counter()

	buildToolchain()

	endTime = time.perf_counter()
	deltaTime = datetime.timedelta(seconds=(endTime - startTime))

	log.info(f"Time to complete: {deltaTime}")

if __name__ == '__main__':
	main()
