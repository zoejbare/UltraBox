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
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#

import os
import platform
import subprocess
import sys

########################################################################################################################

_REPO_ROOT_PATH = os.path.abspath(f"{os.path.dirname(__file__)}/..")

########################################################################################################################

def _runCmd(cmd, failMsg):
	result = subprocess.call(cmd)
	assert \
		result == 0, \
		failMsg

########################################################################################################################

def main():
	makefilePath = os.path.normpath(f"{_REPO_ROOT_PATH}/make.py")

	# Determine which build toolchain we need to use based on the platform that is currently running this script.
	buildToolchain = {
		"Windows": "msvc",
		"Darwin": "clang",
	}.get(platform.system(), "gcc")

	# Construct the build command, but only select the release target since that's what
	# the other build tools will ultimately look for. The other targets technically work,
	# but no other tools will see those.
	cmd = [
		sys.executable,
		makefilePath,
		"-o", buildToolchain,
		"-t", "release",
		"-r",
	]

	# Build the project native tools.
	_runCmd(cmd, "Failed to build UltraBox tools")

########################################################################################################################

if __name__ == "__main__":
	main()
