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
.. module:: n64_assembler
	:synopsis: N64 assembler tool

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os

from csbuild import log
from csbuild.tools.assemblers.assembler_base import AssemblerBase
from csbuild.tools.common.tool_traits import HasDebugLevel
from csbuild._utils import response_file, shared_globals

from n64_tool_base import N64BaseTool

DebugLevel = HasDebugLevel.DebugLevel

class N64Assembler(N64BaseTool, AssemblerBase):
	"""
	N64 assembler implementation.
	"""
	supportedArchitectures = {"mips"}
	inputFiles={".s", ".S"}
	outputFiles = {".o"}

	def __init__(self, projectSettings):
		N64BaseTool.__init__(self, projectSettings)
		AssemblerBase.__init__(self, projectSettings)

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getOutputFiles(self, project, inputFile):
		outputPath = os.path.join(project.GetIntermediateDirectory(inputFile), os.path.splitext(os.path.basename(inputFile.filename))[0])

		return tuple({ "{}.o".format(outputPath) })

	def _getCommand(self, project, inputFile):
		args = self._getInputFileArgs(inputFile) \
			+ self._getDefaultArgs() \
			+ self._getCustomArgs() \
			+ self._getOutputFileArgs(project, inputFile) \
			+ self._getPreprocessorArgs() \
			+ self._getIncludeDirectoryArgs()

		inputFileBasename = os.path.basename(inputFile.filename)
		responseFile = response_file.ResponseFile(project, "{}-{}".format(inputFile.uniqueDirectoryId, inputFileBasename), args)

		if shared_globals.showCommands:
			log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

		return [self._n64GccExePath, "@{}".format(responseFile.filePath)]

	def SetupForProject(self, project):
		N64BaseTool.SetupForProject(self, project)
		AssemblerBase.SetupForProject(self, project)

	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getDefaultArgs(self):
		args = ["--pass-exit-codes"]
		return args

	def _getPreprocessorArgs(self):
		args = [
			"-D_ULTRA64",
			"-D__EXTENSIONS__",
			"-D_LANGUAGE_ASSEMBLY",
			"-D_MIPS_SZLONG=32",
			"-D_MIPS_SZINT=32",
		]
		args.extend([f"-D{x}" for x in self._defines])
		args.extend([f"-U{x}" for x in self._undefines])
		return args

	def _getIncludeDirectoryArgs(self):
		args = [
			f"-I{self._n64SysrootIncludePath}",
		]
		args.extend([f"-I{x}" for x in self._includeDirectories])
		return args

	def _getInputFileArgs(self, inputFile):
		return ["-c", "{}".format(inputFile.filename)]

	def _getOutputFileArgs(self, project, inputFile):
		outputFiles = self._getOutputFiles(project, inputFile)
		return ["-o", outputFiles[0]]

	def _getCustomArgs(self):
		return self._asmFlags
