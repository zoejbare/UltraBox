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

import clint
import contextlib
import os
import shutil
import stat
import subprocess
import sys
import threading

from . import log

@contextlib.contextmanager
def changeDirectory(destPath):
	"""
	Move to a specific directory within a scoped context block,
	moving back to the original directory at the end of the block.

	:param destPath: Destination directory to move into temporarily.
	:type destPath: str
	"""
	destPath = os.path.abspath(destPath)
	oldPath = os.getcwd()

	# Move to the input path.
	os.chdir(destPath)

	try:
		yield

	finally:
		# Move back to the original path.
		os.chdir(oldPath)

def deletePathOnDisk(rootPath):
	rootPath = os.path.abspath(rootPath)

	# Do nothing if the path doesn't exist.
	if not os.access(rootPath, os.F_OK):
		return

	def addWritePermissions(_path):
		# Add write permissions to the file if it doesn't already have it.
		if not os.access(_path, os.W_OK):
			st = os.stat(_path)
			os.chmod(_path, st.st_mode | stat.S_IWUSR)
			return True

		return False

	def deleteFile(_path):
		try:
			os.remove(_path)

		except:
			if addWritePermissions(_path):
				os.remove(_path)

			else:
				raise

	log.info(f"Deleting: {rootPath}")

	assert os.access(rootPath, os.F_OK), f"Cannot delete path; path does not exist: {rootPath}"

	if os.path.isdir(rootPath):
		dirPaths = set()
		filePaths = set()

		# Discover all directories and files in the path to be deleted.
		for root, dirs, files in os.walk(rootPath):
			root = os.path.abspath(root)

			for dirPath in dirs:
				dirPath = os.path.join(root, dirPath)
				dirPaths.add(dirPath)

			for filePath in files:
				filePath = os.path.join(root, filePath)
				filePaths.add(filePath)

		# Directories need to be removed in a specific order converting it to a reverse-sorted list will accomplish that.
		dirPaths = reversed(sorted(dirPaths))

		# Combine all the paths into a single list so it all gets included in the progress bar.
		allPaths = list(filePaths)
		allPaths.extend(dirPaths)
		allPaths.append(rootPath)

		# Delete each file and directory.
		if allPaths:
			for itemPath in clint.textui.progress.bar(allPaths):
				if not os.path.isdir(itemPath):
					deleteFile(itemPath)

				else:
					os.rmdir(itemPath)

	elif os.path.isfile(rootPath):
		deleteFile(rootPath)

	else:
		# We have no idea what this path is pointing to, but it's not something we can handle.
		raise AssertionError(f"Cannot delete path of unknown type: {rootPath}")

def copyFilesOnDisk(srcPath, dstPath):
	srcPath = os.path.abspath(srcPath)
	dstPath = os.path.abspath(dstPath)

	log.info(f"Copying: {srcPath}\n\t-> {dstPath}")

	assert os.access(srcPath, os.F_OK), f"Cannot copy source path; path does not exist: {srcPath}"

	if os.path.isdir(srcPath):
		# Make the destination directory if it doesn't already exist.
		if not os.access(dstPath, os.F_OK):
			os.makedirs(dstPath)

		relFilePaths = set()
		relDirPaths = set()

		# Discover all files and directories in the source path.
		for root, dirs, files in os.walk(srcPath):
			root = os.path.abspath(root)

			for dirPath in dirs:
				dirPath = os.path.relpath(os.path.join(root, dirPath), srcPath)
				relDirPaths.add(dirPath)

			for filePath in files:
				filePath = os.path.relpath(os.path.join(root, filePath), srcPath)
				relFilePaths.add(filePath)

		# Using a reverse-sorted path of directories will make creating them in the destination path quicker.
		relDirPaths = reversed(sorted(relDirPaths))

		# Create the directory tree in the destination path first.
		# This will be extremely quick, so no progress bar is needed.
		for dirPath in relDirPaths:
			dirPath = os.path.join(dstPath, dirPath)

			if not os.access(dirPath, os.F_OK):
				os.makedirs(dirPath)

		# Copy the files from the source path to the destination path.
		for filePath in clint.textui.progress.bar(relFilePaths):
			srcFilePath = os.path.join(srcPath, filePath)
			dstFilePath = os.path.join(dstPath, filePath)

			shutil.copy2(srcFilePath, dstFilePath)

	elif os.path.isfile(srcPath):
		shutil.copy(srcPath, dstPath)

	else:
		# We have no idea what this path is pointing to, but it's not something we can handle.
		raise AssertionError(f"Cannot copy path of unknown type: {srcPath}")

def runProcess(cmd, outputHandler=log.rawMessage, errorHandler=log.rawError, **kwargs):
	"""
	Wrapper for launching a process and listening for output and errors in realtime.

	:param cmd: Command to launch.
	:type cmd: list[str]

	:param outputHandler: Function to receive stdout from the launched process.
	:type outputHandler: callable

	:param errorHandler: Function to receive stderr frokm the launched process.
	:type errorHandler: callable

	:return: Process return code.
	:rtype: int
	"""
	def streamOutput(pipe, handler):
		while True:
			line = pipe.readline()

			if not line:
				break

			if handler:
				if sys.version_info[0] >= 3:
					line = line.decode("utf-8", "replace")

				# Strip out the '\r' characters on Windows since some
				# stdout/stderr streams will interpret them as newlines.
				line = line.replace("\r", "")

				handler(line)

	def removeArg(arg):
		if arg in kwargs:
			del kwargs[arg]

	# Remove stdout and stderr from kwargs since we set them explicitly.
	removeArg("stdout")
	removeArg("stderr")

	# If launching through a new shell, concatenate the command arguments into a single string.
	isShell = kwargs.get("shell", False)
	if isShell is True:
		cmd = " ".join(cmd)

	proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)

	outputThread = threading.Thread(target=streamOutput, args=(proc.stdout, outputHandler))
	errorThread = threading.Thread(target=streamOutput, args=(proc.stderr, errorHandler))

	outputThread.start()
	errorThread.start()

	outputThread.join()
	errorThread.join()

	proc.wait()

	proc.stdout.close()
	proc.stderr.close()

	return proc.returncode
