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
import hashlib
import os
import py7zr
import requests
import tarfile
import zipfile

from py7zr.callbacks import ExtractCallback

from . import log

class DownloadableArchive(object):
	def __init__(self, downloadPath, tokenPath, url):
		assert downloadPath, "No root download path provided"
		assert url, "No URL provided"

		self._url = url
		self._packageName = os.path.basename(self._url)
		self._downloadFilePath = os.path.join(downloadPath, self._packageName)
		self._tokenFilePath = os.path.join(tokenPath, f"{os.path.basename(self._downloadFilePath)}.token")
		self._unpackHandler = None

		unpackHandlers = {
			self._unpackZip: [".zip"],
			self._unpackTar: [".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"],
			self._unpack7z: [".7z"],
		}

		# Figure out which unpack function can handle the input file.
		for func, exts in unpackHandlers.items():
			for ext in exts:
				if self._packageName.endswith(ext):
					self._unpackHandler = func
					break

		assert self._unpackHandler is not None, f"No unpack handler defined for file: {self._packageName}"

	@property
	def filePath(self):
		return self._downloadFilePath

	def download(self, force):
		if not self._url:
			log.error("Cannot download file, empty URL")
			return

		checksumFilePath = f"{self._downloadFilePath}.md5"

		if not force and os.access(self._downloadFilePath, os.F_OK):
			validCheck, expectedChecksum, actualChecksum = self._validateChecksum(checksumFilePath, self._downloadFilePath)

			if validCheck:
				if expectedChecksum == actualChecksum:
					log.info(f"File up-to-date, skipping download for: {self._packageName}, checksum: {actualChecksum}")
					return

				else:
					log.warning(f"Checksum verification failed: {actualChecksum}, expected: {expectedChecksum}")

			else:
				log.warning(f"Missing cached checksum for: {self._downloadFilePath}")

		log.info(f"Downloading {self._packageName} ...")

		req = requests.get(self._url, allow_redirects=True, stream=True)
		chunkSize = 1024
		downloadSize = int(req.headers.get("content-length"))
		progressBarSize = (downloadSize / chunkSize) + 1

		hasher = hashlib.md5()

		# Stream the file to disk which updating the hasher to calculate the file's checksum.
		with open(self._downloadFilePath, "wb") as outputStream:
			for chunk in clint.textui.progress.bar(req.iter_content(chunk_size=chunkSize), expected_size=progressBarSize):
				if chunk:
					hasher.update(chunk)
					outputStream.write(chunk)
					outputStream.flush()

		# Write the file's checksum to disk.
		with open(checksumFilePath, "w") as outputStream:
			outputStream.write(hasher.hexdigest())

	def _validateChecksum(self, checksumFilePath, rootPath):
		if os.access(checksumFilePath, os.F_OK):
			with open(checksumFilePath, "r") as inputStream:
				expectedChecksum = inputStream.read()

			log.verbose(f"Verifying checksum for: {rootPath}")

			actualChecksum = self._getChecksum(rootPath)
			return True, expectedChecksum, actualChecksum

		return False, None, None

	def _saveChecksum(self, checksumFilePath, checksum):
		with open(checksumFilePath, "w") as outputStream:
			outputStream.write(checksum)

	def _getChecksum(self, path):
		hasher = hashlib.md5()

		filePaths = set()

		if os.path.isdir(path):
			for root, _, files in os.walk(path):
				for file in files:
					filePaths.add(os.path.join(root, file))

		else:
			filePaths.add(path)

		# Calculate the hash of all the detected file paths
		for filePath in filePaths:
			with open(filePath, "rb") as inputStream:
				while True:
					data = inputStream.read(32768)
					if not data:
						break

					hasher.update(data)

		return hasher.hexdigest()

	def unpack(self, unpackPath):
		if os.access(self._tokenFilePath, os.F_OK):
			log.verbose(f"Skipping unpack for package {os.path.basename(self._downloadFilePath)}; token already exists")
			return

		if not os.access(self._downloadFilePath, os.F_OK):
			raise FileNotFoundError(f"Cannot unpack, missing archive file: {self._downloadFilePath}")

		log.info(f"Unpacking {os.path.basename(self._downloadFilePath)} ...")
		self._unpackHandler(unpackPath)

		# Write a token file to indicate the path exists now.
		with open(self._tokenFilePath, "w") as f:
			pass

	def _prepareUnpackPath(self, unpackRootPath, filename):
		unpackPath = os.path.dirname(os.path.join(unpackRootPath, filename))

		if not os.access(unpackPath, os.F_OK):
			os.makedirs(unpackPath)

	def _unpackZip(self, unpackRootPath):
		with zipfile.ZipFile(self._downloadFilePath, "r") as inputArchive:
			fileInfoList = inputArchive.infolist()

			for fileInfo in clint.textui.progress.bar(fileInfoList):
				self._prepareUnpackPath(unpackRootPath, fileInfo.filename)
				inputArchive.extract(fileInfo.filename, unpackRootPath)

	def _unpackTar(self, unpackRootPath):
		with tarfile.open(self._downloadFilePath, "r") as inputArchive:
			fileInfoList = inputArchive.getmembers()

			for fileInfo in clint.textui.progress.bar(fileInfoList):
				try:
					inputArchive.extract(fileInfo.name, unpackRootPath)
				except KeyError as e:
					log.warning(f"(TAR) {e}")

	def _unpack7z(self, unpackRootPath):
		class CallbackImpl(ExtractCallback):
			def __init__(self, count, progress):
				self._fileIndex = 0
				self._fileCount = count
				self._progress = progress

			def report_start_preparation(self):
				pass

			def report_start(self, processing_file_path, processing_bytes):
				pass

			def report_end(self, processing_file_path, wrote_bytes):
				self._fileIndex += 1
				self._progress.show(self._fileIndex)

			def report_warning(self, message):
				log.warning(f"(7Z) {message}")

			def report_postprocess(self):
				pass

		with py7zr.SevenZipFile(self._downloadFilePath, "r") as inputArchive:
			fileCount = len(inputArchive.list())
			progressBar = clint.textui.progress.Bar(expected_size=fileCount)
			callbacks = CallbackImpl(fileCount, progressBar)

			inputArchive.extractall(unpackRootPath, callbacks)
			progressBar.done()
