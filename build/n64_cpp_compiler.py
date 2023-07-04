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
.. module:: xbox_360_cpp_compiler
	:synopsis: Xbox 360 compiler tool for C++

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import os

from csbuild import log
from csbuild.tools.cpp_compilers.cpp_compiler_base import CppCompilerBase
from csbuild.tools.common.tool_traits import HasDebugLevel, HasOptimizationLevel
from csbuild._utils import response_file, shared_globals

from n64_tool_base import N64BaseTool

DebugLevel = HasDebugLevel.DebugLevel
OptimizationLevel = HasOptimizationLevel.OptimizationLevel

def _ignore(_):
	pass

class N64CppCompiler(N64BaseTool, CppCompilerBase):
	"""
	N64 compiler tool implementation.
	"""
	supportedArchitectures = { "mips" }
	outputFiles = { ".o" }

	def __init__(self, projectSettings):
		N64BaseTool.__init__(self, projectSettings)
		CppCompilerBase.__init__(self, projectSettings)

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def _getOutputFiles(self, project, inputFile):
		intDirPath = project.GetIntermediateDirectory(inputFile)
		filename = os.path.splitext(os.path.basename(inputFile.filename))[0] + ".o"
		return tuple({ os.path.join(intDirPath, filename) })

	def _getCommand(self, project, inputFile, isCpp):
		cmdExe = self._getComplierName(project, isCpp)
		cmd = self._getInputFileArgs(inputFile) \
			+ self._getDefaultArgs() \
			+ self._getCustomArgs(project, isCpp) \
			+ self._getArchitectureArgs() \
			+ self._getOptimizationArgs() \
			+ self._getDebugArgs() \
			+ self._getLanguageStandardArgs(isCpp) \
			+ self._getOutputFileArgs(project, inputFile) \
			+ self._getPreprocessorArgs(isCpp) \
			+ self._getIncludeDirectoryArgs()

		inputFileBasename = os.path.basename(inputFile.filename)
		responseFile = response_file.ResponseFile(project, "{}-{}".format(inputFile.uniqueDirectoryId, inputFileBasename), cmd)

		if shared_globals.showCommands:
			log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

		return [cmdExe, "@{}".format(responseFile.filePath)]

	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getComplierName(self, project, isCpp):
		_ignore(project)
		return self._n64GppExePath if isCpp else self._n64GccExePath

	def _getDefaultArgs(self):
		args = [
			"--pass-exit-codes",
			"-ffreestanding",
			"-G0",
		]
		return args

	def _getCustomArgs(self, project, isCpp):
		_ignore(project)
		return self._globalFlags + (self._cxxFlags if isCpp else self._cFlags)

	def _getInputFileArgs(self, inputFile):
		return ["-c", inputFile.filename]

	def _getOutputFileArgs(self, project, inputFile):
		outputFiles = self._getOutputFiles(project, inputFile)
		return ["-o", outputFiles[0]]

	def _getPreprocessorArgs(self, isCpp):
		args = [
			"-D_ULTRA64",
			"-D__EXTENSIONS__",
			"-D_LANGUAGE_C_PLUS_PLUS" if isCpp else "-D_LANGUAGE_C",
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

	def _getDebugArgs(self):
		if self._debugLevel != DebugLevel.Disabled:
			return ["-g"]
		return []

	def _getOptimizationArgs(self):
		arg = {
			OptimizationLevel.Size: "s",
			OptimizationLevel.Speed: "fast",
			OptimizationLevel.Max: "3",
		}.get(self._optLevel, "0")
		return [f"-O{arg}"]

	def _getArchitectureArgs(self):
		args = [
			"-mabi=32",
			"-march=vr4300",
			"-mtune=vr4300",
			"-mfix4300",
		]
		return args

	def _getLanguageStandardArgs(self, isSourceCpp):
		standard = self._cxxStandard if isSourceCpp else self._ccStandard
		arg = "-std={}".format(standard) if standard else None
		return [arg]
