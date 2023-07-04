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
.. module:: n64_linker
	:synopsis: N64 linker tool for compiled C/C++ and assembly.

.. moduleauthor:: Zoe Bare
"""

from __future__ import unicode_literals, division, print_function

import platform

import csbuild
import os
import re

from csbuild import commands, log
from csbuild.tools.linkers.linker_base import LinkerBase
from csbuild.tools.common.tool_traits import HasDebugLevel
from csbuild._utils import ordered_set, response_file, shared_globals

from n64_tool_base import N64BaseTool

DebugLevel = HasDebugLevel.DebugLevel

class N64Linker(N64BaseTool, LinkerBase):
	"""
	N64 linker tool implementation for compiled c/c++ and asm.
	"""
	supportedArchitectures = {"mips"}
	inputGroups = {".o", ".ld"}
	outputFiles = {".elf", ".a"}
	crossProjectDependencies = {".a"}

	_failRegex = re.compile(R"ld: cannot find -l(.*)")

	####################################################################################################################
	### Methods implemented from base classes
	####################################################################################################################

	def __init__(self, projectSettings):
		N64BaseTool.__init__(self, projectSettings)
		LinkerBase.__init__(self, projectSettings)

	def _getOutputFiles(self, project):
		assert project.projectType != csbuild.ProjectType.SharedLibrary, "N64 does not support shared libraries"

		outputPath = os.path.join(project.outputDir, project.outputName)
		outputFiles = {
			csbuild.ProjectType.Application: ["{}.elf".format(outputPath)],
			csbuild.ProjectType.StaticLibrary: ["{}.a".format(outputPath)],
		}[project.projectType]

		return tuple(outputFiles)

	def _getCommand(self, project, inputFiles):
		if project.projectType == csbuild.ProjectType.StaticLibrary:
			cmdExe = self._n64ArExePath
			cmd = ["rcs"] \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles)
		else:
			cmdExe = self._n64GccExePath
			cmd = self._getDefaultArgs() \
				+ self._getCustomArgs() \
				+ self._getLinkerScriptArgs(project, inputFiles) \
				+ self._getOutputFileArgs(project) \
				+ self._getInputFileArgs(inputFiles) \
				+ self._getLibraryPathArgs() \
				+ self._getStartGroupArgs() \
				+ self._getLibraryArgs() \
				+ self._getEndGroupArgs()

		responseFile = response_file.ResponseFile(project, "linker-{}".format(project.outputName), cmd)

		if shared_globals.showCommands:
			log.Command("ResponseFile: {}\n\t{}".format(responseFile.filePath, responseFile.AsString()))

		return [cmdExe, "@{}".format(responseFile.filePath)]

	def _findLibraries(self, project, libs):
		ret = {}

		shortLibs = ordered_set.OrderedSet(libs)
		longLibs = []

		for lib in libs:
			if os.access(lib, os.F_OK) and not os.path.isdir(lib):
				abspath = os.path.abspath(lib)
				ret[lib] = abspath
				shortLibs.remove(lib)

			elif os.path.splitext(lib)[1]:
				shortLibs.remove(lib)
				longLibs.append(lib)

		if platform.system() == "Windows":
			nullOut = os.path.join(project.csbuildDir, "null")
		else:
			nullOut = "/dev/null"

		if shortLibs:
			# In most cases this should be finished in exactly two attempts.
			# However, in some rare cases, ld will get to a successful lib after hitting a failure and just give up.
			# -lpthread is one such case, and in that case we have to do this more than twice.
			# However, the vast majority of cases should require only two calls (and only one if everything is -lfoo format)
			# and the vast majority of the cases that require a third pass will not require a fourth... but, everything
			# is possible! Still better than doing a pass per file like we used to.
			while True:
				cmd = [self._n64LdExePath, "--verbose", "-M", "-o", nullOut] + \
					  ["-L"+path for path in self._getLibrarySearchDirectories()] + \
					  ["-l"+lib for lib in shortLibs] + \
					  ["-l:"+lib for lib in longLibs]
				returncode, out, err = commands.Run(cmd, None, None)
				if returncode != 0:
					lines = err.splitlines()
					moved = False
					for line in lines:
						match = N64Linker._failRegex.match(line)
						if match:
							lib = match.group(1)
							if lib not in shortLibs:
								for errorLine in lines:
									log.Error(errorLine)
								return None
							shortLibs.remove(lib)
							longLibs.append(lib)
							moved = True

					if not moved:
						for line in lines:
							log.Error(line)
						return None

					continue
				break

			matches = []

			try:
				# All bfd linkers should have the link maps showing where libraries load from.  Most linkers will be
				# bfd-based, so first assume that is the output we have and try to parse it.
				loading = False
				inGroup = False
				for line in out.splitlines():
					if line.startswith("LOAD"):
						if inGroup:
							continue
						loading = True
						matches.append(line[5:])
					elif line == "START GROUP":
						inGroup = True
					elif line == "END GROUP":
						inGroup = False
					elif loading:
						break

				assert len(matches) == len(shortLibs) + len(longLibs)
				assert len(matches) + len(ret) == len(libs)

			except AssertionError:
				# Fallback to doing the traditional regex check when the link map check failes.
				# All bfd- and gold-compatible linkers should have this.
				succeedRegex = re.compile("(?:.*ld(?:.exe)?): Attempt to open (.*) succeeded")
				for line in err.splitlines():
					match = succeedRegex.match(line)
					if match:
						matches.append(match.group(1))

				assert len(matches) == len(shortLibs) + len(longLibs)
				assert len(matches) + len(ret) == len(libs)

			for i, lib in enumerate(shortLibs):
				ret[lib] = matches[i]
			for i, lib in enumerate(longLibs):
				ret[lib] = matches[i+len(shortLibs)]
			for lib in libs:
				log.Info("Found library '{}' at {}", lib, ret[lib])

		return ret

	def _getOutputExtension(self, projectType):
		# These are extensions of the files that can be output from the linker or librarian.
		# The library extensions should represent the file types that can actually linked against.
		ext = {
			csbuild.ProjectType.Application: ".elf",
			csbuild.ProjectType.StaticLibrary: ".a",
		}
		return ext.get(projectType, None)

	def SetupForProject(self, project):
		N64BaseTool.SetupForProject(self, project)
		LinkerBase.SetupForProject(self, project)

	####################################################################################################################
	### Internal methods
	####################################################################################################################

	def _getDefaultArgs(self):
		return [
			"-nostdlib",
			"-Wl,--no-as-needed",
		]

	def _getLinkerScriptArgs(self, project, inputFiles):
		linkerScriptFiles = sorted([f.filename for f in inputFiles if f.filename.endswith(".ld")])
		if not linkerScriptFiles:
			return []

		if len(linkerScriptFiles) > 1:
			log.Warn(f"Project '{project.name}' contains more than one linker script; using the first one found: {linkerScriptFiles[0]}")

		args = ["-T", linkerScriptFiles[0]]
		return args

	def _getCustomArgs(self):
		return self._linkerFlags

	def _getLibraryArgs(self):
		args = ["-l:{}".format(os.path.basename(lib)) for lib in self._actualLibraryLocations.values()]
		return args

	def _getLibraryPathArgs(self):
		args = [
			f"-L{self._n64SysrootLibPath}",
			f"-L{self._n64GccLibPath}",
		]
		args.extend(["-L{}".format(os.path.dirname(libFile)) for libFile in self._actualLibraryLocations.values()])
		return args

	def _getLibrarySearchDirectories(self):
		dirs = [
			self._n64SysrootLibPath,
			self._n64GccLibPath,
		]
		dirs.extend(self._libraryDirectories)
		return dirs

	def _getOutputFileArgs(self, project):
		outFile = self._getOutputFiles(project)[0]
		if project.projectType == csbuild.ProjectType.StaticLibrary:
			return [outFile]
		return ["-o", outFile]

	def _getInputFileArgs(self, inputFiles):
		args = [f.filename for f in inputFiles if f.filename.endswith(".o")]
		return args

	def _getStartGroupArgs(self):
		return ["-Wl,-("]

	def _getEndGroupArgs(self):
		return ["-Wl,-)"]
