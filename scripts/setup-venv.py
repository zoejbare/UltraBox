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
import shutil
import subprocess
import sys

########################################################################################################################

_REPO_ROOT_PATH = os.path.abspath(f"{os.path.dirname(__file__)}/..")
_IS_HOST_WSL = "microsoft" in platform.uname().release.lower()

########################################################################################################################

def _runCmd(cmd, failMsg):
	result = subprocess.call(cmd)
	assert \
		result == 0, \
		failMsg

########################################################################################################################

def _getEnvPython(envPath):
	pythonExePath = {
		"Windows": os.path.join(envPath, "Scripts", "python.exe")
	}.get(platform.system(), os.path.join(envPath, "bin", "python"))
	return pythonExePath

########################################################################################################################

def removeOldBuildEnv(buildPath):
	print("Removing old build environment ...")
	shutil.rmtree(buildPath, ignore_errors=True)

########################################################################################################################

def createVirtualEnv(buildPath):
	pythonExePath = _getEnvPython(buildPath)

	print("Building Python virtual environment ...")

	# Create the virtual environment.
	cmd = [
		sys.executable,
		"-m", "venv",
		buildPath,
	]
	_runCmd(cmd, "Failed to create Python virtual environment")

	# Upgrade the core packages in the virtual environment.
	cmd = [
		pythonExePath,
		"-m", "pip",
		"install",
		"-U",
		"pip",
		"wheel",
		"setuptools",
	]
	_runCmd(cmd, "Failed to upgrade Python virtual environment core packages")

########################################################################################################################

def installDependencies(buildPath, externalPath):
	csbuildPath = os.path.join(externalPath, "csbuild2")
	pythonExePath = _getEnvPython(buildPath)

	# Install the some required packages to the virtual environment.
	cmd = [
		pythonExePath,
		"-m", "pip",
		"install",
		"requests",
		"clint",
		"py7zr",
	]
	_runCmd(cmd, "Failed to install required packages from PIP to Python virtual environment")

	# Install csbuild to the virtual environment.
	cmd = [
		pythonExePath,
		"-m", "pip",
		"install", "-e",
		csbuildPath,
	]
	_runCmd(cmd, "Failed to install 'csbuild' to Python virtual environment")

########################################################################################################################

def main():
	outputDirName = "_venv-wsl" if _IS_HOST_WSL else "_venv"
	externalPath = os.path.normpath(f"{_REPO_ROOT_PATH}/external")
	buildPath = os.path.normpath(f"{_REPO_ROOT_PATH}/{outputDirName}")

	# Setup a local Python environment.
	removeOldBuildEnv(buildPath)
	createVirtualEnv(buildPath)
	installDependencies(buildPath, externalPath)

########################################################################################################################

if __name__ == "__main__":
	main()
