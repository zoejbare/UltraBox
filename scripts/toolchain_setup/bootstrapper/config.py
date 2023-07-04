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

import multiprocessing
import platform
import os
import subprocess

_THIS_PATH = os.path.abspath(os.path.dirname(__file__))

class Config(object):
	_Instance = None

	def __init__(self):
		systemName = platform.system()
		maxCoreCount = multiprocessing.cpu_count()

		self._isHostWindows = systemName == "Windows"
		self._isHostLinux = systemName == "Linux"
		self._isHostMacOs = systemName == "Darwin"
		self._hostMachineSpec = ""
		self._cachePath = ""
		self._installPath = ""
		self._cpuCount = maxCoreCount
		self._maxCpuCount = maxCoreCount

		self.forceDownload = False
		self.windowsCrossCompile = False

		try:
			# Get the machine spec to pass to the project configs.
			self._hostMachineSpec = subprocess.check_output(["gcc", "-dumpmachine"]).decode("utf-8").strip()

		except:
			# The host machine spec is only needed when building specific toolchains. If this is missing
			# when attempting to build those toolchains, an error will be issued at that time.
			pass

	@classmethod
	def getInstance(cls):
		if not cls._Instance:
			cls._Instance = Config()
		return cls._Instance

	@property
	def isHostWindows(self):
		return self._isHostWindows

	@property
	def isHostLinux(self):
		return self._isHostLinux

	@property
	def isHostMacOs(self):
		return self._isHostMacOs

	@property
	def hostMachineSpec(self):
		return self._hostMachineSpec

	@property
	def cachePath(self):
		return self._cachePath

	@cachePath.setter
	def cachePath(self, path):
		self._cachePath = os.path.abspath(path)

	@property
	def installPath(self):
		return self._installPath

	@installPath.setter
	def installPath(self, path):
		self._installPath = os.path.abspath(path)

	@property
	def cpuCoreCount(self):
		return self._cpuCount

	@cpuCoreCount.setter
	def cpuCoreCount(self, count):
		self._cpuCount = min(count, self._maxCpuCount) if count > 0 else self._maxCpuCount

	@property
	def maxCpuCoreCount(self):
		return self._maxCpuCount
