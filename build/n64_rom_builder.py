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

"""
.. module:: n64_rom_builder
	:synopsis: N64 ROM builder tool

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import platform

import csbuild
import os
import warnings

from csbuild import commands, log
from csbuild.tools.common.tool_traits import HasDebugLevel
from csbuild._utils.decorators import TypeChecked

from n64_tool_base import N64BaseTool

DebugLevel = HasDebugLevel.DebugLevel

_THIS_PATH = os.path.abspath(os.path.dirname(__file__))

warnings.filterwarnings("ignore")

class N64RomBuilder(N64BaseTool):
	"""
	Tool that converts a raw N64 ELF to a padded N64 ROM with a valid header, checksum, and bootcode.

	:param projectSettings: A read-only scoped view into the project settings dictionary
	:type projectSettings: toolchain.ReadOnlySettingsView
	"""
	supportedArchitectures = { "mips" }
	inputFiles = { ".elf" }
	outputFiles = { ".z64" }

	################################################################################
	### Initialization
	################################################################################

	def __init__(self, projectSettings):
		N64BaseTool.__init__(self, projectSettings)

		self._n64GameTitle = projectSettings.get("n64GameTitle", None)
		self._n64GameCode = projectSettings.get("n64GameCode", None)
		self._n64RomVersion = projectSettings.get("n64RomVersion", 0)
		self._n64BootCodeId = projectSettings.get("n64BootCodeId", 6102)
		self._n64BootCodeFile = None

		exeFileExt = ".exe" if platform.system() == "Windows" else ""

		self._maskRom64ExePath = os.path.abspath(f"{_THIS_PATH}/../output/tool/release/maskrom64{exeFileExt}")
		assert os.access(self._maskRom64ExePath, os.F_OK), f"Cannot find the MaskRom64 tool at: {self._maskRom64ExePath}"

	####################################################################################################################
	### Static makefile methods
	####################################################################################################################

	@staticmethod
	@TypeChecked(title=str)
	def SetN64GameTitle(title):
		"""
		Set the game title to write into the output ROM header.
		Game titles may not exceed 20 characters in the ROM header, so any titles longer than that will be truncated.

		:param title: Title of the game.
		:type title: str
		"""
		csbuild.currentPlan.SetValue("n64GameTitle", title)

	@staticmethod
	@TypeChecked(code=str)
	def SetN64GameCode(code):
		"""
		Set the game code to write into the output ROM header.
		Must be exactly 4 characters long.

		:param code: 4-character game code.
		:type code: str
		"""
		csbuild.currentPlan.SetValue("n64GameCode", code)

	@staticmethod
	@TypeChecked(version=int)
	def SetN64RomVersion(version):
		"""
		Set the version number of the ROM.
		This is inserted into the ROM header as a single byte, so only first 8 bits of this value are used.

		:param version: Version number.
		:type version: str
		"""
		csbuild.currentPlan.SetValue("n64RomVersion", version)

	@staticmethod
	@TypeChecked(id=int)
	def SetN64BootCodeId(id):
		"""
		Set the ID of the bootcode to write into the output ROM.

		:param id: ID of the bootcode to use.
		:type id: int
		"""
		csbuild.currentPlan.SetValue("n64BootCodeId", id)

	################################################################################
	### Internal methods
	################################################################################

	def _getOutputFile(self, project, inputFile):
		inputFileExtSplit = os.path.splitext(os.path.basename(inputFile.filename))
		outputFilePath = os.path.join(
			project.outputDir,
			"{}.z64".format(inputFileExtSplit[0])
		)
		return outputFilePath

	################################################################################
	### Base class methods containing logic shared by all subclasses
	################################################################################

	def SetupForProject(self, project):
		N64BaseTool.SetupForProject(self, project)

		# Use an assertion on the game code since its length is more strictly defined.
		if self._n64GameCode:
			assert len(self._n64GameCode) == 4, f"N64 game code is not exactly 4 characters long: \"{self._n64GameCode}\""

		# Game titles longer than 20 bytes will be truncated.
		if self._n64GameTitle and len(self._n64GameTitle) > 20:
			log.Warn(f"N64 game title exceeds 20 characters: \"{self._n64GameTitle}\"")

		# Any values for the ROM version larger than the maximum value
		# for an unsigned byte will be truncated to their first 8 bits.
		if self._n64RomVersion > 255:
			log.Warn(f"ROM version exceeds 255: {self._n64RomVersion}")

		self._n64BootCodeFile = os.path.normpath(f"{_THIS_PATH}/bootcode/{self._n64BootCodeId}CIC.BIN")
		assert os.access(self._n64BootCodeFile, os.F_OK), f"Cannot find N64 bootcode file: {self._n64BootCodeFile}"

	def Run(self, inputProject, inputFile):
		"""
		Execute a single build step. Note that this method is run massively in parallel with other build steps.
		It is NOT thread-safe in ANY way. If you need to change shared state within this method, you MUST use a
		mutex.

		:param inputProject: project being built
		:type inputProject: csbuild._build.project.Project
		:param inputFile: File to build
		:type inputFile: input_file.InputFile
		:return: tuple of files created by the tool - all files must have an extension in the outputFiles list
		:rtype: tuple[str]

		:raises BuildFailureException: Build process exited with an error.
		"""
		outputFilePath = self._getOutputFile(inputProject, inputFile)

		log.Build(
			"Converting {} to N64 ROM ({}-{}-{})...",
			os.path.basename(inputFile.filename),
			inputProject.toolchainName,
			inputProject.architectureName,
			inputProject.targetName
		)

		objCopyCmd = [
			self._n64ObjCopyExePath,
			"-O", "binary",
			inputFile.filename,
			outputFilePath
		]

		# Part 1/2: Convert the ELF to a raw Z64 binary.
		returncode, _, _ = commands.Run(objCopyCmd, cwd=inputProject.outputDir)
		if returncode != 0:
			raise csbuild.BuildFailureException(inputProject, inputFile)

		log.Build(
			"Masking {} ({}-{}-{})...",
			os.path.basename(outputFilePath),
			inputProject.toolchainName,
			inputProject.architectureName,
			inputProject.targetName
		)

		maskRomCmd = [
			self._maskRom64ExePath,
			outputFilePath,
			"-o", outputFilePath,
			"-b", self._n64BootCodeFile,
			"-i", str(self._n64BootCodeId),
			"-r", str(self._n64RomVersion),
			"-q",
		]

		if self._n64GameTitle:
			maskRomCmd.extend(["-t", self._n64GameTitle])

		if self._n64GameCode:
			maskRomCmd.extend(["-g", self._n64GameCode])

		# Part 2/2: Mask the ROM with bootcode and a valid checksum.
		returncode, _, _ = commands.Run(maskRomCmd, cwd=inputProject.outputDir)
		if returncode != 0:
			raise csbuild.BuildFailureException(inputProject, inputFile)

		return tuple({ outputFilePath })
