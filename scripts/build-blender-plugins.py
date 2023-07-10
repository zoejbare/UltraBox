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
import shutil
import zipfile

########################################################################################################################

_REPO_ROOT_PATH = os.path.abspath(f"{os.path.dirname(__file__)}/..")

########################################################################################################################

def main():
	pluginSrcRootPath = os.path.normpath(f"{_REPO_ROOT_PATH}/tools/blender")
	pluginBuildRootPath = os.path.normpath(f"{_REPO_ROOT_PATH}/plugins/blender")

	if os.access(pluginBuildRootPath, os.F_OK):
		print("Removing old plugin builds ...")
		shutil.rmtree(pluginBuildRootPath)

	print("Finding plugins sources ...")
	srcPaths = [
		os.path.normpath(f"{pluginSrcRootPath}/{x}")
		for x in os.listdir(pluginSrcRootPath)
		if not x.startswith("_")
	]
	srcPaths = [x for x in srcPaths if os.path.isdir(x)]

	if srcPaths:
		# Create the output root directory.
		os.makedirs(pluginBuildRootPath)

		# Build each Blender plugin.
		for pluginPath in srcPaths:
			print(f"Building plugin: \"{os.path.basename(pluginPath)}\" ...")

			outputFileName = f"{os.path.basename(pluginPath)}.zip"
			outputFilePath = os.path.normpath(f"{pluginBuildRootPath}/{outputFileName}")

			pluginSrcFiles = set()

			# Discover each file in the current plugin directory.
			for root, _, files in os.walk(pluginPath):
				for filePath in files:
					if filePath.endswith(".py"):
						pluginSrcFiles.add(os.path.join(root, filePath))

			# Build a zip file containing all the plugin source files.
			with zipfile.ZipFile(outputFilePath, mode = "w") as zf:
				for srcFilePath in pluginSrcFiles:
					zf.write(srcFilePath, arcname = os.path.relpath(srcFilePath, os.path.normpath(f"{pluginPath}/..")))

	else:
		print("[WARNING] No Blender plugins found")

########################################################################################################################

if __name__ == "__main__":
	main()
